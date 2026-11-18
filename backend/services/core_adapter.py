"""Thin, synchronous adapters. Core imports stay lazy for health/OpenAPI.

Use one server worker: embedded Qdrant owns an exclusive process lock.
Serialize core access in this process, including ingestion and shutdown.
"""

import sys
from threading import RLock

from backend.schemas.api import (
    ChatRequest, ChatResponse, DocumentsResponse, ExportRequest,
    FlashcardsRequest, FlashcardsResponse, LearningRequest, QuizRequest,
    QuizResponse, SourceSelection, SummaryRequest, SummaryResponse, UploadResponse, MindMapRequest, MindMapResponse,
)

_core_lock = RLock()


class AdapterError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def documents() -> DocumentsResponse:
    from src.store import list_documents

    with _core_lock:
        return DocumentsResponse(documents=list_documents())


def _filters(selection: SourceSelection) -> dict[str, object]:
    from src.filters import filters_to_dict
    from src.store import list_documents

    indexed = {item["filename"]: item for item in list_documents()}
    if any(name not in indexed for name in selection.filenames):
        raise AdapterError(404, "Selected document is not indexed.")
    if selection.pages and selection.pages[0] not in indexed[selection.filenames[0]]["pages"]:
        raise AdapterError(404, "Selected page is not indexed.")
    values: dict[str, object] = {"filenames": selection.filenames}
    if selection.pages:
        values["page"] = selection.pages[0]
    return filters_to_dict(values)


def upload(content: bytes, filename: str) -> UploadResponse:
    from src.indexing import save_and_ingest_pdf

    with _core_lock:
        return UploadResponse.model_validate(save_and_ingest_pdf(content, filename))


def chat(request: ChatRequest) -> ChatResponse:
    from src.rag import answer

    with _core_lock:
        result = answer(request.question, k=request.k, filters=_filters(request))
        # Private chunks contain metadata.source absolute paths; do not publish them.
        return ChatResponse.model_validate(result.model_dump(exclude={"chunks"}))


def _learning_args(request: LearningRequest) -> dict:
    return {"query": request.topic, "filters": _filters(request), "k": request.k}


def summary(request: SummaryRequest) -> SummaryResponse:
    from src.learning import summarize

    with _core_lock:
        return SummaryResponse.model_validate(summarize(**_learning_args(request)).model_dump())


def quiz(request: QuizRequest) -> QuizResponse:
    from src.learning import generate_quiz

    with _core_lock:
        return QuizResponse.model_validate(generate_quiz(count=request.count, **_learning_args(request)).model_dump())


def flashcards(request: FlashcardsRequest) -> FlashcardsResponse:
    from src.learning import generate_flashcards

    with _core_lock:
        return FlashcardsResponse.model_validate(generate_flashcards(count=request.count, **_learning_args(request)).model_dump())


def mindmap(request: MindMapRequest) -> MindMapResponse:
    from src.mindmap import generate_mindmap

    with _core_lock:
        return MindMapResponse.model_validate(generate_mindmap(**_learning_args(request)).model_dump())


def markdown(request: ExportRequest) -> str:
    from src.export import export
    from src.schemas import FlashcardSet, QuizSet, RagAnswer, Summary, MindMap

    models = {"chat": RagAnswer, "summary": Summary, "quiz": QuizSet, "flashcards": FlashcardSet, "mindmap": MindMap}
    result = models[request.feature].model_validate(request.result.model_dump())
    # No output path: canonical renderer returns text without filesystem writes.
    rendered = export(result, fmt="md")
    if request.feature == "chat" and request.result.context:
        context = request.result.context
        rendered += "\n\n## Phạm vi đọc chuyên sâu\n\n" + ", ".join(context.filenames) + "\n"
        if context.selection:
            rendered += f"\nĐoạn chọn · trang {context.selection.page}:\n\n"
            rendered += "\n".join("> " + line for line in context.selection.text.splitlines()) + "\n"
    return rendered


def close() -> None:
    with _core_lock:
        store = sys.modules.get("src.store")
        if store is not None:
            store.close_client()
