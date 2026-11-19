"""Create original multi-format teaching materials and an isolated index."""
from contextlib import contextmanager
from io import BytesIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from xml.sax.saxutils import escape
from zipfile import ZipFile,ZipInfo,ZIP_DEFLATED

ROOT=Path(__file__).resolve().parent


def load_fixture():
    import hashlib
    raw=(ROOT/'fixture.json').read_bytes();policy=json.loads((ROOT/'policy.json').read_text())
    if hashlib.sha256(raw).hexdigest()!=policy['fixture_sha256']:raise ValueError('Frozen fixture changed; create a new evaluation version.')
    prompt=ROOT.parents[1]/'src/prompts/answer.jinja2'
    if policy.get('prompt_sha256')!=hashlib.sha256(prompt.read_bytes()).hexdigest():raise ValueError('Frozen evaluation prompt changed; version the policy before new runs.')
    return json.loads(raw),policy


def write_materials(destination):
    """No model calls. All output is original CC0 teaching material."""
    fixture,_=load_fixture();destination=Path(destination);destination.mkdir(parents=True,exist_ok=True)
    paths={}
    for source in fixture['sources']:
        path=destination/source['filename'];paths[source['id']]=path
        if source['format']=='docx':
            xml='<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'
            xml+=''.join('<w:p><w:r><w:t>'+escape(text)+'</w:t></w:r></w:p>' for text in source['blocks'])+'</w:body></w:document>'
            with ZipFile(path,'w',ZIP_DEFLATED) as archive:
                for name,content in {'[Content_Types].xml':'<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>','word/document.xml':xml}.items():
                    info=ZipInfo(name,date_time=(1980,1,1,0,0,0));info.compress_type=ZIP_DEFLATED;archive.writestr(info,content)
        elif source['format']=='pdf':
            from pypdf import PdfWriter
            from pypdf.generic import DecodedStreamObject,DictionaryObject,NameObject
            writer=PdfWriter()
            for lines in source['pages']:
                page=writer.add_blank_page(width=820,height=792)
                font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
                page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):writer._add_object(font)})})
                stream=DecodedStreamObject();stream.set_data(('BT /F1 10 Tf 30 720 Td '+' '.join('('+line.replace('\\','\\\\').replace('(','\\(').replace(')','\\)')+') Tj 0 -28 Td' for line in lines)+' ET').encode('ascii'))
                page[NameObject('/Contents')]=writer._add_object(stream)
            writer.write(path)
        else:path.write_text('\n\n'.join(source['blocks'])+'\n',encoding='utf-8')
    (destination/'LICENSE.txt').write_text('CC0-1.0. Original fictional learning materials authored for YourNote evaluation; no personal/student data.\n')
    return paths


@contextmanager
def isolated_index():
    from src.config import settings
    from src.store import get_client,close_client
    from src.indexing import save_and_ingest_document
    if get_client.cache_info().currsize:raise RuntimeError('Run evaluation in its own process; an index is already open.')
    with TemporaryDirectory(prefix='yournote-phase06-') as directory,patch.object(settings,'storage_dir',Path(directory)/'storage/qdrant'),patch.object(settings,'data_dir',Path(directory)/'data'):
        try:
            mapping={key:save_and_ingest_document(path.read_bytes(),path.name) for key,path in write_materials(Path(directory)/'materials').items()}
            yield mapping
        finally:close_client()


def case_scope(case,mapping):
    scope={'filenames':[mapping[key]['filename'] for key in case['sources']],
        'document_versions':{mapping[key]['filename']:mapping[key]['document_version'] for key in case['sources']}}
    if case['pages']:scope['page']=case['pages'][0]
    return scope


def case_history(case,mapping):
    # Controlled seeded completed turns, not fresh model-generated answers.
    return [{'question':turn['question'],'answer':turn['answer'],'filenames':[mapping[key]['filename'] for key in turn['sources']]} for turn in case['history']]


def evidence_metrics(case,chunks,mapping):
    from src.grounding import normalized
    expected=case['expected_evidence'];hits=[]
    for ref in expected:
        hits.append(any(chunk.metadata.filename==mapping[ref['source']]['filename'] and normalized(ref['quote']) in normalized(chunk.text) and (not ref.get('locator') or all(getattr(chunk.metadata.locator,key,None)==value for key,value in ref['locator'].items())) for chunk in chunks))
    scope=case_scope(case,mapping)
    leaks=sum(chunk.metadata.filename not in scope['filenames'] or chunk.metadata.document_version!=scope['document_versions'].get(chunk.metadata.filename) or bool(case['pages'] and chunk.metadata.page not in case['pages']) for chunk in chunks)
    return {'evidence_units':len(expected),'evidence_found':sum(hits),'evidence_hit':int(any(hits)) if expected else None,'evidence_recall':sum(hits)/len(expected) if expected else None,'scope_leaks':leaks}
