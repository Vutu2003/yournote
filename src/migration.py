"""Offline, idempotent Phase 04 migration with verifiable whole-store rollback."""
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3

from src.config import settings
from src.data_guard import data_guard
from src import documents as catalog


def _checksum(path):
    digest=hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda:source.read(1024*1024),b''): digest.update(block)
    return digest.hexdigest()


def _safe_tree(root):
    if root.exists() and (root.is_symlink() or any(p.is_symlink() for p in root.rglob('*'))):
        raise ValueError('Backup refuses symbolic links in document storage.')


@contextmanager
def _qdrant_closed():
    lock=settings.storage_dir/'.lock'
    if not lock.exists(): yield;return
    with lock.open('r+b') as handle:
        try: fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError: raise RuntimeError('Embedded Qdrant is open. Stop all data processes before backup.') from None
        try: yield
        finally: fcntl.flock(handle,fcntl.LOCK_UN)


def backup(destination:Path):
    if destination.exists(): raise ValueError('Backup destination must not exist.')
    root=settings.storage_dir.resolve().parent
    if destination.resolve().is_relative_to(settings.storage_dir.resolve()) or destination.resolve().is_relative_to(settings.data_dir.resolve()):
        raise ValueError('Backup destination must be outside data and Qdrant.')
    for source in (settings.storage_dir,settings.data_dir): _safe_tree(source)
    with _qdrant_closed():
        destination.mkdir(parents=True,mode=0o700)
        manifest={'schema_version':2,'created_at':datetime.now(timezone.utc).isoformat(),'present':{},'sha256':{}}
        for name,source in [('qdrant',settings.storage_dir),('data',settings.data_dir),('notebooks.sqlite',root/'notebooks.sqlite'),('documents.sqlite',catalog.database_path())]:
            manifest['present'][name]=source.exists()
            if not source.exists(): continue
            target=destination/name
            if source.is_dir(): shutil.copytree(source,target,ignore=shutil.ignore_patterns('.lock'))
            else:
                # Even a cleanly stopped SQLite may have WAL pages; use its backup API.
                with sqlite3.connect(source.resolve().as_uri()+'?mode=ro',uri=True) as original, sqlite3.connect(target) as snapshot:
                    original.backup(snapshot)
        for path in destination.rglob('*'):
            if path.is_file(): manifest['sha256'][str(path.relative_to(destination))]=_checksum(path);path.chmod(0o600)
        (destination/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');(destination/'manifest.json').chmod(0o600)
    return manifest


def verify_backup(destination):
    manifest=json.loads((destination/'manifest.json').read_text())
    if manifest.get('schema_version')!=2: raise ValueError('Unsupported backup schema.')
    for name,digest in manifest['sha256'].items():
        path=(destination/name).resolve()
        if not path.is_relative_to(destination.resolve()) or not path.is_file() or _checksum(path)!=digest:
            raise ValueError('Backup checksum validation failed.')
    return manifest


def migrate(*,backup_directory:Path):
    from src.store import close_client, list_documents
    # Caller must not have an open in-process client. Never close someone else's active app.
    from src.store import get_client
    if get_client.cache_info().currsize: raise RuntimeError('Close the index before offline migration.')
    with data_guard(offline=True):
        backup(backup_directory)
        marker=settings.storage_dir.resolve().parent/'.phase04-incomplete'
        marker.write_text('offline migration in progress\n')
        migrated=0;missing=0
        try:
            rows=list_documents()
            for row in rows:
                if catalog.get_document(filename=row['filename']): continue
                path=(settings.data_dir/row['filename']).resolve()
                if path.parent!=settings.data_dir.resolve() or not path.is_file(): missing+=1;continue
                if path.suffix.lower()!='.pdf': raise ValueError('Unregistered legacy source is not a PDF.')
                content=path.read_bytes();version=hashlib.sha256(content).hexdigest()
                archived=catalog.archive(content,row['filename'],version)
                from src.document_parser import parse_file,DocumentParseError
                try: parsed=parse_file(path)
                except DocumentParseError: parsed={'blocks':[],'page_count':max(row['pages'],default=0)}
                doc={'id':row['document_id'],'filename':row['filename'],'original_filename':row['filename'],'kind':'pdf','legacy_version':version}
                catalog.commit_document(doc,{'version':version,'relative_path':archived,'blocks':parsed['blocks'],
                    'page_count':parsed['page_count'],'chunk_count':row['chunk_count'],'warnings':[]})
                migrated+=1
            catalog.check_embedding_contract(record=True)
        finally: close_client()
        marker.unlink(missing_ok=True)
        return {'schema_version':2,'registered':migrated,'original_unavailable':missing,'backup_verified':bool(verify_backup(backup_directory))}


def rollback(backup_directory:Path):
    from src.store import get_client
    if get_client.cache_info().currsize: raise RuntimeError('Close the index before rollback.')
    with data_guard(offline=True),_qdrant_closed():
        manifest=verify_backup(backup_directory)
        root=settings.storage_dir.resolve().parent
        # Preserve current files before replacing anything, allowing recovery of a failed restore.
        recovery=root/'backups'/('pre-rollback-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f'))
        recovery.mkdir(parents=True,mode=0o700)
        marker=root/'.phase04-incomplete'
        marker.write_text('offline restore in progress\n')
        targets={'qdrant':settings.storage_dir,'data':settings.data_dir,'notebooks.sqlite':root/'notebooks.sqlite','documents.sqlite':catalog.database_path()}
        for name,target in targets.items():
            if target.exists(): shutil.move(str(target),str(recovery/name))
            for suffix in ('-wal','-shm'):
                side=Path(str(target)+suffix)
                if side.exists(): shutil.move(str(side),str(recovery/(name+suffix)))
            if manifest['present'].get(name):
                target.parent.mkdir(parents=True,exist_ok=True)
                if (backup_directory/name).is_dir(): shutil.copytree(backup_directory/name,target)
                else: shutil.copy2(backup_directory/name,target)
        marker.unlink(missing_ok=True)
        return {'restored':True,'recovery_directory':str(recovery)}
