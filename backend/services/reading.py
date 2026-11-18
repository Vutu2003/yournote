"""Read only notebook-owned PDFs; annotations never alter the original file."""

from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re
import unicodedata
from uuid import uuid4

from pypdf import PdfReader

from backend.schemas.api import ChatContext, ChatResponse, SourceSelection
from backend.schemas.reading import Highlight, HighlightCreate, ReadingChatRequest, ReadingDocument
from backend.services import core_adapter, notebooks
from backend.services.core_adapter import AdapterError
from src.config import settings


@lru_cache(maxsize=64)
def _inspect(path: str, modified: int, size: int) -> tuple[str, int]:
    del modified, size  # These cache keys invalidate fingerprints after a file changes.
    digest = hashlib.sha256()
    with open(path, "rb") as original:
        for block in iter(lambda: original.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest(), len(PdfReader(path).pages)


def document(notebook_id: str, document_id: str) -> tuple[ReadingDocument, Path]:
    notebook = notebooks.get_notebook(notebook_id)
    indexed = core_adapter.documents().documents
    found = next((doc for doc in indexed if doc.document_id == document_id and doc.filename in notebook.state.document_filenames), None)
    if found is None:
        raise AdapterError(404, "Document is not in this notebook.")
    root = settings.data_dir.resolve()
    path = (root / found.filename).resolve()
    if path.parent != root or not path.is_file():
        raise AdapterError(404, "Original PDF is unavailable.")
    try:
        stat = path.stat()
        version, pages = _inspect(str(path), stat.st_mtime_ns, stat.st_size)
    except Exception as exc:
        raise AdapterError(400, "Unable to read original PDF.") from exc
    return ReadingDocument(document_id=document_id, filename=found.filename, document_version=version, page_count=pages), path


def _highlight(row) -> Highlight:
    return Highlight(id=row["id"], document_id=row["document_id"], document_version=row["document_version"], page=row["page"], text=row["text"], rects=json.loads(row["rects"]), created_at=row["created_at"])


def highlights(notebook_id: str, document_id: str) -> list[Highlight]:
    info, _ = document(notebook_id, document_id)
    with notebooks._database() as connection:
        rows = connection.execute("SELECT * FROM pdf_highlights WHERE notebook_id = ? AND document_id = ? AND document_version = ? ORDER BY page, created_at", (notebook_id, document_id, info.document_version))
        return [_highlight(row) for row in rows]


def create_highlight(notebook_id: str, document_id: str, request: HighlightCreate) -> Highlight:
    info, _ = document(notebook_id, document_id)
    if request.document_version != info.document_version:
        raise AdapterError(409, "Original PDF has changed. Reopen the document.")
    if request.page > info.page_count:
        raise AdapterError(422, "Page is outside the original PDF.")
    identifier = str(uuid4())
    with notebooks._database() as connection:
        connection.execute("INSERT INTO pdf_highlights VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (identifier, notebook_id, document_id, info.document_version, request.page, request.text, json.dumps([rect.model_dump() for rect in request.rects]), notebooks._now()))
        return _highlight(connection.execute("SELECT * FROM pdf_highlights WHERE id = ?", (identifier,)).fetchone())


def delete_highlight(notebook_id: str, document_id: str, highlight_id: str) -> None:
    document(notebook_id, document_id)
    with notebooks._database() as connection:
        result = connection.execute("DELETE FROM pdf_highlights WHERE id = ? AND notebook_id = ? AND document_id = ?", (highlight_id, notebook_id, document_id))
        if result.rowcount == 0:
            raise AdapterError(404, "Highlight not found.")


def _normalized(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).casefold().replace("-\n", "")
    return re.sub(r"[\s\u00ad]+", "", text)


def chat(notebook_id: str, request: ReadingChatRequest) -> ChatResponse:
    from src.rag import answer, answer_from_chunks
    from src.schemas import ChunkMetadata, RetrievedChunk

    info, path = document(notebook_id, request.document_id)
    notebook = notebooks.get_notebook(notebook_id)
    names = [info.filename] if request.scope == "document" else notebook.state.document_filenames
    with core_adapter._core_lock:
        if request.selection:
            selected = request.selection
            if selected.document_id != info.document_id or selected.filename != info.filename:
                raise AdapterError(422, "Selected passage belongs to a different document.")
            if selected.document_version != info.document_version:
                raise AdapterError(409, "Original PDF has changed. Reopen the document.")
            if selected.page > info.page_count:
                raise AdapterError(422, "Page is outside the original PDF.")
            reader = PdfReader(path)
            page_text = reader.pages[selected.page - 1].extract_text() or ""
            if not _normalized(selected.text) or _normalized(selected.text) not in _normalized(page_text):
                raise AdapterError(422, "Selected text could not be matched to the original PDF.")
            chunks = []
            # Include the preceding/following page for definitions and continued text.
            for page in range(max(1, selected.page - 1), min(info.page_count, selected.page + 1) + 1):
                text = page_text if page == selected.page else (reader.pages[page - 1].extract_text() or "")
                if text.strip():
                    chunks.append(RetrievedChunk(text=text, score=0, metadata=ChunkMetadata(document_id=info.document_id, filename=info.filename, source=str(path), page=page, chunk_id=f"{info.document_id}:{page}:reading")))
            result = answer_from_chunks(request.question, chunks, selected_text=selected.text)
        else:
            filters = core_adapter._filters(SourceSelection(filenames=names))
            result = answer(request.question, k=request.k, filters=filters)
    return ChatResponse(**result.model_dump(exclude={"chunks"}), context=ChatContext(scope=request.scope, filenames=names, selection=request.selection))
