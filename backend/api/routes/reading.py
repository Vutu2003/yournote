"""Split PDF reading, original downloads, annotations and scoped conversations."""

from fastapi import APIRouter, Response
from fastapi.responses import FileResponse

from backend.schemas.api import ChatResponse, ERROR_RESPONSES, ErrorResponse
from backend.schemas.reading import Highlight, HighlightCreate, HighlightsResponse, ReadingChatRequest, ReadingDocument
from backend.services import reading

router = APIRouter(prefix="/api/notebooks/{notebook_id}", tags=["Reading"], responses={**ERROR_RESPONSES, 409: {"model": ErrorResponse, "description": "Original PDF version has changed"}})


@router.get("/documents/{document_id}", response_model=ReadingDocument, summary="Inspect an original PDF in this notebook")
def document(notebook_id: str, document_id: str):
    return reading.document(notebook_id, document_id)[0]


@router.get("/documents/{document_id}/pdf", summary="Read or download the unmodified original PDF", response_class=FileResponse, responses={200: {"content": {"application/pdf": {}}}})
def original_pdf(notebook_id: str, document_id: str, download: bool = False, version: str | None = None):
    info, path = reading.document(notebook_id, document_id)
    if version and version != info.document_version:
        from backend.services.core_adapter import AdapterError
        raise AdapterError(409, "Original PDF has changed. Reopen the document.")
    return FileResponse(path, media_type="application/pdf", filename=info.filename, content_disposition_type="attachment" if download else "inline", headers={"ETag": f'"{info.document_version}"', "X-Content-Type-Options": "nosniff", "Cache-Control": "private, no-cache"})


@router.get("/documents/{document_id}/highlights", response_model=HighlightsResponse, summary="List highlights for the current PDF version")
def highlights(notebook_id: str, document_id: str):
    return HighlightsResponse(highlights=reading.highlights(notebook_id, document_id))


@router.post("/documents/{document_id}/highlights", response_model=Highlight, status_code=201, summary="Save a yellow highlight without changing the PDF")
def create_highlight(notebook_id: str, document_id: str, request: HighlightCreate):
    return reading.create_highlight(notebook_id, document_id, request)


@router.delete("/documents/{document_id}/highlights/{highlight_id}", status_code=204, summary="Delete a highlight in this notebook")
def delete_highlight(notebook_id: str, document_id: str, highlight_id: str):
    reading.delete_highlight(notebook_id, document_id, highlight_id)
    return Response(status_code=204)


@router.post("/reading/chat", response_model=ChatResponse, summary="Ask about the open PDF or a verified selected passage")
def chat(notebook_id: str, request: ReadingChatRequest):
    return reading.chat(notebook_id, request)
