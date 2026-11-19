"""Structure-aware ingestion with immutable originals and per-document updates."""
from __future__ import annotations

from collections import defaultdict
import hashlib
from pathlib import Path
import tempfile
from typing import Protocol
import uuid

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client.http import models as qmodels

from src.config import settings
from src.document_parser import KINDS, MAX_BYTES, DocumentParseError, parse_file
from src import documents as catalog
from src.locks import index_operation
from src.schemas import ChunkMetadata
from src.store import ensure_collection, get_client, get_vector_store


class Chunker(Protocol):
    def split_documents(self, documents: list[Document]) -> list[Document]: ...


def _splitter(chunk_size=None,chunk_overlap=None):
    return RecursiveCharacterTextSplitter(chunk_size=chunk_size or settings.chunk_size,
        chunk_overlap=settings.chunk_overlap if chunk_overlap is None else chunk_overlap,
        separators=['\n\n','\n','. ',' ',''],keep_separator=False)


def _document_id(path:Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _chunk_id(doc_id,page,index):
    return f'{doc_id}:{page}:{index}'


def _documents(parsed,*,document_id,filename,source,version):
    return [Document(page_content=block['text'],metadata={
        'document_id':document_id,'filename':filename,'source':str(source),'document_version':version,
        'page':block['locator'].get('page'),'locator':block['locator'],'schema_version':2,
        'section':' / '.join(block['locator'].get('heading',[])) or None,
    }) for block in parsed['blocks']]


def _make_chunks(pages,chunk_size=None,chunk_overlap=None,chunker=None):
    # Split inside paragraphs/headings instead of merging across structural anchors.
    chunks=(chunker or _splitter(chunk_size,chunk_overlap)).split_documents(pages)
    counters=defaultdict(int)
    for chunk in chunks:
        meta=chunk.metadata;doc_id=meta['document_id'];index=counters[doc_id];counters[doc_id]+=1
        locator=meta.get('locator') or {}
        position=locator.get('anchor') or meta.get('page') or 'text'
        digest=hashlib.sha256(chunk.page_content.encode()).hexdigest()[:12]
        meta['chunk_id']=f"{doc_id}:{meta.get('document_version','legacy')}:{position}:{digest}:{index}"
        chunk.metadata=ChunkMetadata(**meta).model_dump(exclude_none=True)
    if len(chunks)>5000: raise DocumentParseError('Document exceeds the 5000 chunk limit.')
    return chunks


def _load_pdf(path:Path):
    parsed=parse_file(path);version=_document_id(path)
    return _documents(parsed,document_id=version,filename=path.name,source=path.resolve(),version=version)


def discover_pdfs(data_dir=None):
    directory=data_dir or settings.data_dir
    return sorted(p for p in directory.iterdir() if p.is_file() and p.suffix.lower()=='.pdf') if directory.exists() else []


def build_chunks(pdf_paths,chunk_size=None,chunk_overlap=None,chunker=None):
    pages=[]
    for path in pdf_paths:
        parsed=parse_file(path);version=_document_id(path)
        pages.extend(_documents(parsed,document_id=version,filename=path.name,source=path.resolve(),version=version))
    return _make_chunks(pages,chunk_size,chunk_overlap,chunker)


def index_chunks(chunks,collection_name=None):
    if not chunks: return 0
    ids=[str(uuid.uuid5(uuid.NAMESPACE_DNS,c.metadata['chunk_id'])) for c in chunks]
    get_vector_store(collection_name=collection_name).add_documents(chunks,ids=ids)
    return len(chunks)


@index_operation
def save_and_ingest_document(file_bytes:bytes,filename:str,*,replace_document_id=None,expected_version=None,collection_name=None,chunker=None,chunk_size=None,chunk_overlap=None):
    # Shared validation for API, CLI and tests. Nothing reaches data_dir before parsing succeeds.
    if not filename or len(filename)>255 or Path(filename).name!=filename or '\\' in filename or any(ord(c)<32 or ord(c)==127 for c in filename):
        raise DocumentParseError('A valid filename without a path is required.')
    name=collection_name or settings.qdrant_collection
    suffix=Path(filename).suffix.lower()
    if suffix not in KINDS: raise DocumentParseError('Supported formats: PDF, DOCX, Markdown and TXT.')
    if len(file_bytes)>MAX_BYTES: raise DocumentParseError('File exceeds the 25 MiB upload limit.')
    with tempfile.TemporaryDirectory(prefix='yournote-parse-') as directory:
        temporary=Path(directory)/('source'+suffix);temporary.write_bytes(file_bytes)
        parsed=parse_file(temporary)
    version=hashlib.sha256(file_bytes).hexdigest()
    previous=catalog.get_document(document_id=replace_document_id) if replace_document_id else None
    if replace_document_id and (not previous or not expected_version or previous['active_version']!=expected_version):
        raise DocumentParseError('Document version changed. Refresh before replacing it.')
    if previous and previous['kind']!=parsed['kind']:
        raise DocumentParseError('A replacement must keep the original document format.')
    if not previous:
        previous=next((doc for doc in catalog.all_documents() if doc['kind']==parsed['kind'] and doc['active_version']==version),None)
    if previous and previous['active_version']==version:
        stored=catalog.get_version(previous['id'])
        client=get_client()
        matching=qmodels.Filter(must=[qmodels.FieldCondition(key='metadata.document_id',match=qmodels.MatchValue(value=previous['id']))])
        if not previous.get('legacy_version') or previous['legacy_version']!=version:
            matching.must.append(qmodels.FieldCondition(key='metadata.document_version',match=qmodels.MatchValue(value=version)))
        actual=client.count(name,count_filter=matching,exact=True).count if client.collection_exists(name) else 0
        if actual==stored['chunk_count']:
            return {'filename':previous['filename'],'document_id':previous['id'],'document_version':version,
                    'original_filename':previous['original_filename'],'chunks_indexed':stored['chunk_count'],'deduplicated':True,'warnings':stored['warnings']}
    identifier=previous['id'] if previous else hashlib.sha256((parsed['kind']+':'+version).encode()).hexdigest()
    key=previous['filename'] if previous else Path(filename).stem[:100]+'--'+version[:16]+suffix
    existing=catalog.get_document(filename=key)
    if existing and existing['id']!=identifier: raise DocumentParseError('Document identity conflict; choose another filename.')
    path=catalog.archive(file_bytes,filename,version)
    chunks=_make_chunks(_documents(parsed,document_id=identifier,filename=key,source=settings.data_dir/path,version=version),chunk_size,chunk_overlap,chunker)
    ensure_collection(collection_name=name)
    catalog.check_embedding_contract(name,record=True)
    count=index_chunks(chunks,collection_name=name)
    doc=previous or {'id':identifier,'filename':key,'original_filename':filename,'kind':parsed['kind']}
    catalog.commit_document(doc,{'version':version,'relative_path':path,'blocks':parsed['blocks'],
        'page_count':parsed['page_count'],'chunk_count':count,'warnings':parsed['warnings']},expected_version=expected_version if replace_document_id else None)
    # Commit first: after a crash, readers still accept only the active version.
    get_client().delete(collection_name=name,points_selector=qmodels.FilterSelector(filter=qmodels.Filter(
        must=[qmodels.FieldCondition(key='metadata.document_id',match=qmodels.MatchValue(value=identifier))],
        must_not=[qmodels.HasIdCondition(has_id=[str(uuid.uuid5(uuid.NAMESPACE_DNS,c.metadata['chunk_id'])) for c in chunks])],
    )))
    return {'filename':key,'document_id':identifier,'document_version':version,'original_filename':doc['original_filename'],
            'chunks_indexed':count,'deduplicated':False,'warnings':parsed['warnings']}


def save_and_ingest_pdf(file_bytes,filename):
    """Compatibility entry point; accepts the expanded document formats too."""
    return save_and_ingest_document(file_bytes,filename)


def ingest(recreate=False,collection_name=None,chunker=None,chunk_size=None,chunk_overlap=None):
    # The catalog, including archive-only uploads, is authoritative when rebuilding.
    jobs={}
    for doc in catalog.all_documents():
        stored=catalog.get_version(doc['id'])
        jobs[doc['id']]=(catalog.original_path(stored),doc['original_filename'],doc)
    paths=sorted(p for p in settings.data_dir.iterdir() if p.is_file() and p.suffix.lower() in KINDS) if settings.data_dir.exists() else []
    for path in paths:
        existing=catalog.get_document(filename=path.name)
        if existing:
            digest=_document_id(path)
            # Original legacy files remain on disk after an explicit UI update.
            # Do not accidentally revert the active version when rebuilding.
            if digest in {existing['active_version'],existing.get('legacy_version')}: continue
            jobs[existing['id']]=(path,path.name,existing)
        else: jobs['new:'+path.name]=(path,path.name,None)
    ensure_collection(recreate=recreate,collection_name=collection_name)
    count=0
    for path,filename,existing in jobs.values():
        result=save_and_ingest_document(path.read_bytes(),filename,
            replace_document_id=existing['id'] if existing else None,
            expected_version=existing['active_version'] if existing else None,
            collection_name=collection_name,chunker=chunker,chunk_size=chunk_size,chunk_overlap=chunk_overlap)
        count+=result['chunks_indexed']
    return count
