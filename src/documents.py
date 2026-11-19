"""Immutable originals and a versioned catalog, independent of embeddings/LLMs.

Reading an absent catalog never creates data. Writes occur under core_lock.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3

from src.config import settings

SCHEMA_VERSION=2


def database_path() -> Path:
    return settings.storage_dir.parent/'documents.sqlite'


@contextmanager
def database(*,write=False):
    path=database_path()
    if not write and not path.is_file():
        yield None;return
    if write: path.parent.mkdir(parents=True,exist_ok=True)
    connection=sqlite3.connect(path if write else path.resolve().as_uri()+'?mode=ro',uri=not write,timeout=10)
    if write: path.chmod(0o600)
    connection.row_factory=sqlite3.Row
    try:
        if write:
            connection.executescript('''
                CREATE TABLE IF NOT EXISTS catalog_meta (key TEXT PRIMARY KEY,value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,filename TEXT NOT NULL UNIQUE,original_filename TEXT NOT NULL,
                    kind TEXT NOT NULL,active_version TEXT NOT NULL,legacy_version TEXT);
                CREATE TABLE IF NOT EXISTS document_versions (
                    document_id TEXT NOT NULL,version TEXT NOT NULL,relative_path TEXT NOT NULL,
                    blocks TEXT NOT NULL,page_count INTEGER NOT NULL,chunk_count INTEGER NOT NULL,
                    warnings TEXT NOT NULL,created_at TEXT NOT NULL,PRIMARY KEY(document_id,version));
            ''')
            connection.execute("INSERT OR IGNORE INTO catalog_meta VALUES ('schema_version',?)",(str(SCHEMA_VERSION),))
        version=connection.execute("SELECT value FROM catalog_meta WHERE key='schema_version'").fetchone()
        if not version or int(version[0])!=SCHEMA_VERSION: raise ValueError('Unsupported document catalog schema.')
        yield connection
        if write: connection.commit()
    except Exception:
        connection.rollback();raise
    finally: connection.close()


def get_document(*,document_id=None,filename=None):
    with database() as connection:
        if connection is None: return None
        row=connection.execute('SELECT * FROM documents WHERE '+('id=?' if document_id else 'filename=?'),(document_id or filename,)).fetchone()
        return dict(row) if row else None


def all_documents():
    with database() as connection:
        return [dict(row) for row in connection.execute('SELECT * FROM documents ORDER BY filename')] if connection else []


def get_version(document_id, version=None):
    doc=get_document(document_id=document_id)
    if not doc: return None
    with database() as connection:
        row=connection.execute('SELECT * FROM document_versions WHERE document_id=? AND version=?',(document_id,version or doc['active_version'])).fetchone()
        if not row: return None
        item={**doc,**dict(row)}
        item['blocks']=json.loads(item['blocks']);item['warnings']=json.loads(item['warnings'])
        return item


def original_path(version):
    root=settings.data_dir.resolve();path=(root/version['relative_path']).resolve()
    if not path.is_relative_to(root) or not path.is_file(): raise ValueError('Original document is unavailable.')
    if hashlib.sha256(path.read_bytes()).hexdigest()!=version['version']:
        raise ValueError('Archived document failed its content checksum.')
    return path


def archive(content:bytes,filename:str,version:str) -> str:
    root=settings.data_dir.resolve();directory=root/'.versions'/version
    directory.mkdir(parents=True,exist_ok=True,mode=0o700)
    directory.parent.chmod(0o700)
    path=directory/filename
    if path.exists():
        if hashlib.sha256(path.read_bytes()).hexdigest()!=version: raise ValueError('Archive checksum mismatch.')
    else:
        # Filename has already been validated; immutable files are never overwritten.
        with path.open('xb') as output: output.write(content)
        path.chmod(0o600)
    return str(path.relative_to(root))


def commit_document(doc,version,*,expected_version=None):
    with database(write=True) as connection:
        existing=connection.execute('SELECT active_version FROM documents WHERE id=?',(doc['id'],)).fetchone()
        if expected_version is not None and (not existing or existing[0]!=expected_version):
            raise ValueError('Document version changed. Refresh before replacing it.')
        connection.execute('INSERT OR IGNORE INTO document_versions VALUES (?,?,?,?,?,?,?,?)',(
            doc['id'],version['version'],version['relative_path'],json.dumps(version['blocks'],ensure_ascii=False),
            version['page_count'],version['chunk_count'],json.dumps(version.get('warnings',[])),datetime.now(timezone.utc).isoformat()))
        connection.execute('UPDATE document_versions SET chunk_count=? WHERE document_id=? AND version=?',(version['chunk_count'],doc['id'],version['version']))
        connection.execute('INSERT INTO documents VALUES (?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET active_version=excluded.active_version',(
            doc['id'],doc['filename'],doc['original_filename'],doc['kind'],version['version'],doc.get('legacy_version')))


def version_active(metadata) -> bool:
    doc=get_document(filename=metadata.filename)
    if not doc: return True  # Unmigrated legacy points retain their original identity.
    if metadata.document_id!=doc['id']: return False
    return (metadata.document_version or doc.get('legacy_version'))==doc['active_version']


def enrich_info(item:dict) -> dict:
    doc=get_document(filename=item['filename'])
    if not doc: return item
    version=get_version(doc['id'])
    return {**item,'schema_version':SCHEMA_VERSION,'document_id':doc['id'],'document_version':doc['active_version'],
            'original_filename':doc['original_filename'],'kind':doc['kind'],
            'page_count':version['page_count'],'anchor_count':len(version['blocks']) if doc['kind']!='pdf' else 0,
            'warnings':version['warnings']}


def check_embedding_contract(collection_name=None,*,record=False):
    """A same-dimension model change must not silently mix incompatible vectors."""
    key='embedding:'+str(collection_name or settings.qdrant_collection)
    with database(write=record) as connection:
        if connection is None: return
        row=connection.execute('SELECT value FROM catalog_meta WHERE key=?',(key,)).fetchone()
        if row and row[0]!=settings.embedding_model:
            raise ValueError('Embedding model differs from the collection manifest. Use a separate collection and migration.')
        if record: connection.execute('INSERT OR IGNORE INTO catalog_meta VALUES (?,?)',(key,settings.embedding_model))
