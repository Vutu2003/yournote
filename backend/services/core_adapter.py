"""Thin, synchronous adapters. Core imports stay lazy for health/OpenAPI.

Use one server worker: embedded Qdrant owns an exclusive process lock.
Serialize core access in this process, including ingestion and shutdown.
"""

import sys
from src.locks import core_lock, index_operation

from backend.schemas.api import (
    ChatRequest, ChatResponse, DocumentsResponse, ExportRequest,
    FlashcardsRequest, FlashcardsResponse, LearningRequest, QuizRequest,
    QuizResponse, SourceSelection, SummaryRequest, SummaryResponse, UploadResponse, MindMapRequest, MindMapResponse,
)

_core_lock = core_lock


class AdapterError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def documents() -> DocumentsResponse:
    from src.store import list_documents

    with _core_lock:
        return DocumentsResponse(documents=list_documents())


@index_operation
def _filters(selection: SourceSelection) -> dict[str, object]:
    from src.filters import filters_to_dict
    from src.store import list_documents

    indexed = {item["filename"]: item for item in list_documents()}
    if any(name not in indexed for name in selection.filenames):
        raise AdapterError(404, "Selected document is not indexed.")
    for filename, version in selection.document_versions.items():
        if indexed[filename].get('document_version') != version:
            raise AdapterError(409, 'Document version changed. Refresh sources and try again.')
    if selection.pages and selection.pages[0] not in indexed[selection.filenames[0]]["pages"]:
        raise AdapterError(404, "Selected page is not indexed.")
    values: dict[str, object] = {"filenames": selection.filenames}
    if selection.document_versions:
        values["document_versions"] = dict(selection.document_versions)
    if selection.pages:
        values["page"] = selection.pages[0]
    return filters_to_dict(values)


def upload(content: bytes, filename: str) -> UploadResponse:
    from src.indexing import save_and_ingest_pdf

    with _core_lock:
        from src.document_parser import DocumentParseError
        try:
            return UploadResponse.model_validate(save_and_ingest_pdf(content, filename))
        except DocumentParseError as exc:
            raise AdapterError(400, str(exc)) from None


def chat(request: ChatRequest, *, history: list[dict] | None = None) -> ChatResponse:
    from src.rag import answer

    result = answer(request.question, k=request.k, filters=_filters(request), history=history)
    # Private chunks contain metadata.source absolute paths; do not publish them.
    return ChatResponse.model_validate(result.model_dump(exclude={"chunks"}))


def _learning_args(request: LearningRequest) -> dict:
    return {"query": request.topic, "filters": _filters(request), "k": request.k}


def summary(request: SummaryRequest) -> SummaryResponse:
    from src.learning import summarize

    return SummaryResponse.model_validate(summarize(**_learning_args(request)).model_dump())


def quiz(request: QuizRequest) -> QuizResponse:
    from src.learning import generate_quiz

    return QuizResponse.model_validate(generate_quiz(count=request.count, **_learning_args(request)).model_dump())


def flashcards(request: FlashcardsRequest) -> FlashcardsResponse:
    from src.learning import generate_flashcards

    return FlashcardsResponse.model_validate(generate_flashcards(count=request.count, **_learning_args(request)).model_dump())


def mindmap(request: MindMapRequest) -> MindMapResponse:
    from src.mindmap import generate_mindmap

    return MindMapResponse.model_validate(generate_mindmap(**_learning_args(request)).model_dump())


def markdown(request: ExportRequest) -> str:
    from src.export import export
    from src.schemas import FlashcardSet, QuizSet, RagAnswer, Summary, MindMap

    from src.research_schemas import Comparison,StudyReport,KnowledgeGraph
    models = {"graph":KnowledgeGraph,"comparison":Comparison,"report":StudyReport,"chat": RagAnswer, "summary": Summary, "quiz": QuizSet, "flashcards": FlashcardSet, "mindmap": MindMap}
    result = models[request.feature].model_validate(request.result.model_dump(exclude={"generation"}))
    # No output path: canonical renderer returns text without filesystem writes.
    rendered = export(result, fmt="md")
    if request.feature == "chat" and request.result.context:
        context = request.result.context
        rendered += "\n\n## Phạm vi đọc chuyên sâu\n\n" + ", ".join(context.filenames) + "\n"
        if context.selection:
            rendered += f"\nĐoạn chọn · trang {context.selection.page}:\n\n"
            rendered += "\n".join("> " + line for line in context.selection.text.splitlines()) + "\n"
    metadata=request.result.generation
    if metadata and request.feature in ('comparison','report','graph'):
        import html
        values=[('Provider',metadata.provider),('Model yêu cầu',metadata.requested_model),('Model thực tế',metadata.model or ', '.join(metadata.actual_models) or 'Chưa được provider cung cấp'),('Thời điểm',metadata.created_at),('Trạng thái',metadata.status),('Số lời gọi',str(metadata.calls))]
        rendered+='\n## Thông tin lần tạo\n\n'+'\n'.join(f'- {label}: {html.escape(value,quote=False)}' for label,value in values)+'\n'
    return rendered


def close() -> None:
    with _core_lock:
        store = sys.modules.get("src.store")
        if store is not None:
            store.close_client()


@index_operation
def current_versions(selection):
    _filters(selection)
    from src.store import list_documents
    return {item['filename']:item['document_version'] for item in list_documents()
            if item['filename'] in selection.filenames and item.get('document_version')}


def comparison(request,*,progress=None):
    from src.research import compare_documents
    from backend.schemas.api import ComparisonResponse
    return ComparisonResponse.model_validate(compare_documents(request.goal,request.criteria,request.filenames,filters=_filters(request),progress=progress).model_dump())


def report(request,*,progress=None):
    from src.research import create_report
    from backend.schemas.api import ReportResponse
    return ReportResponse.model_validate(create_report(request.goal,request.mode,request.filenames,filters=_filters(request),progress=progress).model_dump())


def graph(request,*,progress=None):
    from src.knowledge import create_knowledge_graph
    from backend.schemas.api import GraphResponse
    return GraphResponse.model_validate(create_knowledge_graph(request.goal,request.filenames,filters=_filters(request),progress=progress).model_dump())
