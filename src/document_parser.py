"""Bounded document extraction in a separate process; never renders document HTML."""
from __future__ import annotations

from io import BytesIO
import json
from pathlib import Path
import re
import subprocess
import sys
from zipfile import BadZipFile, ZipFile
import xml.etree.ElementTree as ET

MAX_BYTES = 25 * 1024 * 1024
MAX_TEXT = 2_000_000
MAX_BLOCKS = 10_000
MAX_PAGES = 500
MAX_ZIP_BYTES = 50 * 1024 * 1024
KINDS = {'.pdf': 'pdf', '.docx': 'docx', '.md': 'markdown', '.txt': 'text'}
MIME_TYPES = {'pdf': 'application/pdf', 'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'markdown': 'text/markdown', 'text': 'text/plain'}


class DocumentParseError(ValueError):
    pass


def _block(text, index, *, page=None, heading=None):
    locator = ({'kind':'page','page':page} if page else
               {'kind':'paragraph','anchor':f'b{index:06d}','paragraph':index,'heading':heading or []})
    return {'text':text,'locator':locator}


def extract(content: bytes, suffix: str) -> dict:
    """Pure parser entry used by the resource-limited worker and fixtures."""
    if not content: raise DocumentParseError('Uploaded file is empty.')
    if len(content) > MAX_BYTES: raise DocumentParseError('File exceeds the 25 MiB upload limit.')
    kind=KINDS.get(suffix.lower())
    if not kind: raise DocumentParseError('Supported formats: PDF, DOCX, Markdown and TXT.')
    blocks=[];pages=0;warnings=[]
    if kind == 'pdf':
        if b'%PDF-' not in content[:1024]: raise DocumentParseError('File does not have a PDF header.')
        from pypdf import PdfReader
        try:
            reader=PdfReader(BytesIO(content), strict=False)
            if reader.is_encrypted: raise DocumentParseError('Encrypted PDFs are not supported.')
            pages=len(reader.pages)
            if pages > MAX_PAGES: raise DocumentParseError('PDF exceeds the 500 page limit.')
            total=0;empty=0
            for number,page in enumerate(reader.pages,1):
                stream=page.get_contents()
                if stream is not None and len(stream.get_data()) > 20*1024*1024:
                    raise DocumentParseError('PDF page content exceeds the extraction limit.')
                text=(page.extract_text() or '').strip();total+=len(text)
                if total > MAX_TEXT: raise DocumentParseError('Extracted text exceeds the 2 million character limit.')
                if text: blocks.append(_block(text,len(blocks)+1,page=number))
                else: empty+=1
            if not blocks: raise DocumentParseError('PDF has no extractable text; scanned pages need OCR before upload.')
            if empty: warnings.append(f'{empty} PDF page(s) have no extractable text and may need OCR.')
        except DocumentParseError: raise
        except Exception: raise DocumentParseError('Unable to parse PDF.') from None
    elif kind == 'docx':
        try:
            with ZipFile(BytesIO(content)) as archive:
                entries=archive.infolist()
                if len(entries)>2048 or sum(e.file_size for e in entries)>MAX_ZIP_BYTES:
                    raise DocumentParseError('DOCX archive exceeds extraction limits.')
                if any(e.flag_bits & 1 or e.file_size>10*1024*1024 or e.file_size>max(1,e.compress_size)*200 for e in entries):
                    raise DocumentParseError('DOCX archive is encrypted or has an unsafe compression ratio.')
                if 'word/document.xml' not in archive.namelist() or '[Content_Types].xml' not in archive.namelist():
                    raise DocumentParseError('File is not a DOCX document.')
                xml=archive.read('word/document.xml')
            if re.search(br'<!\s*(?:DOCTYPE|ENTITY)',xml,re.I): raise DocumentParseError('DOCX contains unsupported XML declarations.')
            tree=ET.fromstring(xml);ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'};heading=[]
            total=0
            for paragraph in tree.findall('.//w:body//w:p',ns):
                # Paragraph order includes table cells. No external relationships, macros or embedded objects are opened.
                parts=[]
                for node in paragraph.iter():
                    if node.tag=='{'+ns['w']+'}t': parts.append(node.text or '')
                    elif node.tag=='{'+ns['w']+'}tab': parts.append('\t')
                    elif node.tag=='{'+ns['w']+'}br': parts.append('\n')
                text=''.join(parts).strip()
                if not text: continue
                style=paragraph.find('w:pPr/w:pStyle',ns)
                match=re.search(r'(?:heading|tiêu đề)\s*([1-6])',style.get('{'+ns['w']+'}val',''),re.I) if style is not None else None
                if match:
                    level=int(match.group(1));heading=heading[:level-1]+[text[:160]]
                total+=len(text)
                if total>MAX_TEXT or len(blocks)>=MAX_BLOCKS: raise DocumentParseError('DOCX text exceeds extraction limits.')
                blocks.append(_block(text,len(blocks)+1,heading=list(heading)))
        except DocumentParseError: raise
        except (BadZipFile,KeyError,ET.ParseError,ValueError): raise DocumentParseError('Unable to parse DOCX.') from None
    else:
        try: text=content.decode('utf-8-sig')
        except UnicodeDecodeError: raise DocumentParseError('Markdown/TXT must use UTF-8 encoding.') from None
        if '\x00' in text or content.startswith((b'%PDF',b'PK\x03\x04')) or sum(ord(c)<32 and c not in '\n\r\t' for c in text)>5:
            raise DocumentParseError('File content is not plain text.')
        if len(text)>MAX_TEXT: raise DocumentParseError('Text exceeds the 2 million character limit.')
        heading=[];pending=[];fence=None
        def flush():
            value='\n'.join(pending).strip();pending.clear()
            if value: blocks.append(_block(value,len(blocks)+1,heading=list(heading)))
        for line in text.splitlines():
            if kind=='markdown':
                marker=re.match(r'^\s*(`{3,}|~{3,})',line)
                if marker:
                    if fence is None: fence=marker[1][0]
                    elif marker[1][0]==fence: fence=None
                title=re.match(r'^\s{0,3}(#{1,6})\s+(.+?)\s*#*$',line) if fence is None else None
                if title:
                    flush();level=len(title[1]);heading=heading[:level-1]+[title[2][:160]]
                    blocks.append(_block(line,len(blocks)+1,heading=list(heading)));continue
            if not line.strip() and fence is None: flush()
            else: pending.append(line)
            if len(blocks)>MAX_BLOCKS: raise DocumentParseError('Text exceeds the paragraph limit.')
        flush()
    if not blocks: raise DocumentParseError('Document has no readable text.')
    if len(blocks)>MAX_BLOCKS: raise DocumentParseError('Document exceeds the paragraph limit.')
    return {'kind':kind,'blocks':blocks,'page_count':pages,'warnings':warnings}


def parse_file(path: Path) -> dict:
    """A malformed PDF/ZIP cannot monopolize the API worker indefinitely."""
    try:
        result=subprocess.run([sys.executable,'-m','src.document_parser',str(path.resolve())],capture_output=True,timeout=30,
                              cwd=str(Path(__file__).resolve().parents[1]),check=False)
        if len(result.stdout)>16*1024*1024: raise DocumentParseError('Parser output exceeds the resource limit.')
        payload=json.loads(result.stdout) if result.stdout else {}
        if result.returncode or 'error' in payload:
            raise DocumentParseError(payload.get('error','Document extraction exceeded time or memory limits.'))
        if not isinstance(payload.get('blocks'),list): raise DocumentParseError('Unable to parse document.')
        return payload
    except subprocess.TimeoutExpired: raise DocumentParseError('Document extraction exceeded the 30 second limit.') from None
    except (json.JSONDecodeError,OSError): raise DocumentParseError('Unable to start document extraction.') from None


if __name__=='__main__':
    try:
        import resource
        resource.setrlimit(resource.RLIMIT_CPU,(20,20))
        resource.setrlimit(resource.RLIMIT_AS,(768*1024*1024,768*1024*1024))
        resource.setrlimit(resource.RLIMIT_FSIZE,(16*1024*1024,16*1024*1024))
        path=Path(sys.argv[1])
        if path.stat().st_size>MAX_BYTES: raise DocumentParseError('File exceeds the 25 MiB upload limit.')
        print(json.dumps(extract(path.read_bytes(),path.suffix),ensure_ascii=False))
    except Exception as exc:
        message=str(exc) if isinstance(exc,DocumentParseError) else 'Unable to parse document.'
        print(json.dumps({'error':message}));sys.exit(1)
