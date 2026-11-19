"""Structural evidence checks. These checks do not prove semantic entailment."""
from functools import lru_cache
import re
import unicodedata
from src import documents as catalog
from src.document_parser import parse_file
from src.locations import Locator


def normalized(value):
    return re.sub(r'\s+','',unicodedata.normalize('NFKC',value))


@lru_cache(maxsize=24)
def _parsed(path,modified,size):
    from pathlib import Path
    return parse_file(Path(path))['blocks']


def version_blocks(version):
    path=catalog.original_path(version)
    if version['blocks']: return version['blocks']
    stat=path.stat()
    return _parsed(str(path),stat.st_mtime_ns,stat.st_size)


def verify_citation(citation,*,allow_legacy=False):
    doc=catalog.get_document(filename=citation.filename)
    if not doc:
        if citation.document_version: raise ValueError('Citation source version is unavailable.')
        return None  # Existing unmigrated PDF is checked by the reading service.
    if citation.document_id and citation.document_id!=doc['id']:
        raise ValueError('Citation identity does not match the selected source.')
    if not citation.document_version and (not allow_legacy or not doc.get('legacy_version')):
        raise ValueError('Citation is missing a source version.')
    version=catalog.get_version(doc['id'],citation.document_version or doc['legacy_version'])
    if not version: raise ValueError('Citation source version is unavailable.')
    locator=citation.locator or (Locator(kind='page',page=citation.page) if citation.page else None)
    if locator is None: raise ValueError('Citation has no source location.')
    if (doc['kind']=='pdf')!=(locator.kind=='page'):
        raise ValueError('Citation location does not match the document format.')
    if not citation.source_text or not normalized(citation.source_text):
        raise ValueError('Legacy citation has no excerpt to verify against the original.')
    blocks=version_blocks(version)
    block=next((item for item in blocks if (
        item['locator'].get('page')==locator.page if locator.kind=='page'
        else item['locator'].get('anchor')==locator.anchor and item['locator'].get('paragraph')==locator.paragraph)),None)
    if not block or normalized(citation.source_text) not in normalized(block['text']):
        raise ValueError('Citation excerpt does not match this source version; it cannot be redirected safely.')
    return version,Locator(**block['locator'])
