"""Document discovery and a single PDF upload."""

from fastapi import APIRouter, File, HTTPException, UploadFile

from backend.schemas.api import DocumentsResponse, ERROR_RESPONSES, UploadResponse, validate_filename
from backend.services import core_adapter

router = APIRouter(prefix="/api/documents", tags=["Documents"], responses=ERROR_RESPONSES)
MAX_UPLOAD_BYTES = 25 * 1024 * 1024


@router.get("", response_model=DocumentsResponse, summary="List indexed documents and available locators")
def list_documents():
    return core_adapter.documents()


@router.post("/upload", response_model=UploadResponse, summary="Upload and index PDF, DOCX, Markdown or TXT")
def upload_document(file: UploadFile = File(...)):
    filename, content = _upload(file)
    return core_adapter.upload(content, filename)


def _upload(file):
    try:
        filename = validate_filename(file.filename or "")
    except ValueError:
        raise HTTPException(400, "A valid PDF/DOCX/Markdown/TXT filename without a path is required.") from None
    from pathlib import Path
    from src.document_parser import KINDS, MIME_TYPES
    kind = KINDS[Path(filename).suffix.lower()]
    accepted = {None, "application/octet-stream", MIME_TYPES[kind]}
    if kind == 'markdown': accepted |= {'text/plain', 'text/x-markdown'}
    if file.content_type not in accepted:
        raise HTTPException(400, "Unsupported file content type.")
    content = file.file.read(MAX_UPLOAD_BYTES + 1)
    if not content: raise HTTPException(400, "Document file must not be empty.")
    if len(content) > MAX_UPLOAD_BYTES: raise HTTPException(400, "File exceeds the 25 MiB upload limit.")
    if kind == 'pdf' and b'%PDF-' not in content[:1024]: raise HTTPException(400, "File does not have a PDF header.")
    return filename, content


@router.post("/{document_id}/versions", response_model=UploadResponse, summary="Explicitly replace one source; preserve historical originals")
def replace_document(document_id: str, expected_version: str, file: UploadFile = File(...)):
    from src.indexing import save_and_ingest_document
    from src.document_parser import DocumentParseError
    filename, content = _upload(file)
    try:
        return save_and_ingest_document(content, filename, replace_document_id=document_id, expected_version=expected_version)
    except DocumentParseError as exc:
        raise HTTPException(400, str(exc)) from None
