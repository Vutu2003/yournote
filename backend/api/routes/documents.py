"""Document discovery and a single PDF upload."""

from fastapi import APIRouter, File, HTTPException, UploadFile

from backend.schemas.api import DocumentsResponse, ERROR_RESPONSES, UploadResponse, validate_filename
from backend.services import core_adapter

router = APIRouter(prefix="/api/documents", tags=["Documents"], responses=ERROR_RESPONSES)
MAX_UPLOAD_BYTES = 25 * 1024 * 1024


@router.get("", response_model=DocumentsResponse, summary="List indexed PDFs and available pages")
def list_documents():
    return core_adapter.documents()


@router.post("/upload", response_model=UploadResponse, summary="Upload and index one PDF",
             description="Accepts one PDF, up to 25 MiB. The core parses and indexes it. Existing same-name files may be overwritten by the unchanged core; indexing is not transactional.")
def upload_document(file: UploadFile = File(..., description="One non-empty PDF file")):
    try:
        filename = validate_filename(file.filename or "")
    except ValueError:
        raise HTTPException(400, "A valid PDF filename without a path is required.") from None
    if file.content_type not in {None, "application/pdf", "application/octet-stream"}:
        raise HTTPException(400, "Unsupported file content type.")
    content = file.file.read(MAX_UPLOAD_BYTES + 1)
    if not content:
        raise HTTPException(400, "PDF file must not be empty.")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(400, "PDF file exceeds the 25 MiB upload limit.")
    if b"%PDF-" not in content[:1024]:
        raise HTTPException(400, "File does not have a PDF header.")
    return core_adapter.upload(content, filename)
