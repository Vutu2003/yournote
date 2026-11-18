"""Retrieval, prompts, citations, and grounded answers."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import re

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from src.config import settings
from src.filters import filters_to_qdrant
from src.llm import invoke_llm
from src.schemas import ChunkMetadata, Citation, RagAnswer, RetrievedChunk
from src.store import get_vector_store, scroll_all

PROMPTS_DIR = Path(__file__).parent / "prompts"
ANSWER_TEMPLATE = "answer.jinja2"

_ABSTRACT_REQUEST = re.compile(r"\babstracts?\b|\b(?:phần|mục)\s+tóm\s+tắt\b", re.IGNORECASE)
_ABSTRACT_HEADING = re.compile(
    r"^\s*(?:\d+[.)]?\s+)?a[ \t]*b[ \t]*s[ \t]*t[ \t]*r[ \t]*a[ \t]*c[ \t]*t\b",
    re.IGNORECASE | re.MULTILINE,
)
_INTRODUCTION_HEADING = re.compile(
    r"^\s*(?:\d+[.)]?\s*)?(?:introduction|giới thiệu|mở đầu)\b",
    re.IGNORECASE | re.MULTILINE,
)


def retrieve(
    query: str,
    k: int | None = None,
    filters: dict[str, object] | None = None,
    collection_name: str | None = None,
) -> list[RetrievedChunk]:
    store = get_vector_store(collection_name=collection_name)
    hits = store.similarity_search_with_score(
        query=query,
        k=k or settings.top_k,
        filter=filters_to_qdrant(filters),
    )
    return [
        RetrievedChunk(
            text=doc.page_content,
            score=float(score),
            metadata=ChunkMetadata(**doc.metadata),
        )
        for doc, score in hits
    ]


def fetch_all_chunks(
    filters: dict[str, object] | None = None,
    collection_name: str | None = None,
) -> list[RetrievedChunk]:
    """Scroll every chunk matching the filter, ordered by filename → page → index."""
    name = collection_name or settings.qdrant_collection
    results: list[RetrievedChunk] = []
    for page in scroll_all(name, scroll_filter=filters_to_qdrant(filters)):
        for point in page:
            payload = point.payload or {}
            meta = payload.get("metadata") or {}
            text = payload.get("page_content") or ""
            if not meta or not text:
                continue
            results.append(RetrievedChunk(text=text, score=0.0, metadata=ChunkMetadata(**meta)))
    results.sort(
        key=lambda r: (
            r.metadata.filename,
            r.metadata.page,
            int(r.metadata.chunk_id.rsplit(":", 1)[-1]),
        )
    )
    return results


def _abstract_chunks(chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
    """Locate abstracts structurally, including papers without an Abstract label.

    Work only with already-filtered chunks. Keep whole source chunks so citations
    remain faithful, and include a continuation page when the introduction has
    not started yet. The answer prompt separates the abstract from front matter.
    """
    documents: dict[str, list[RetrievedChunk]] = {}
    for chunk in chunks:
        documents.setdefault(chunk.metadata.document_id, []).append(chunk)

    selected: list[RetrievedChunk] = []
    for document in documents.values():
        labelled = [
            c for c in document
            if (c.metadata.section or "").strip().casefold() == "abstract"
        ]
        if labelled:
            selected.extend(labelled)
            continue

        heading = next((c for c in document if _ABSTRACT_HEADING.search(c.text)), None)
        if heading is None and not any(c.metadata.page == 1 for c in document):
            # A page filter must never silently expand to other pages.
            continue
        start_page = heading.metadata.page if heading else 1
        opening = [c for c in document if c.metadata.page == start_page]
        if heading:
            # Ignore any introduction belonging to front matter before Abstract.
            start = document.index(heading)
            opening = [c for c in document[start:] if c.metadata.page == start_page]
            text = "\n".join(c.text for c in opening)
            text = text[_ABSTRACT_HEADING.search(text).end():]
        else:
            text = "\n".join(c.text for c in opening)
        selected.extend(opening)
        if not _INTRODUCTION_HEADING.search(text):
            selected.extend(c for c in document if c.metadata.page == start_page + 1)
    return selected


@lru_cache(maxsize=1)
def _jinja_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(PROMPTS_DIR)),
        autoescape=False,
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )


def render_prompt(template_name: str, **context: object) -> str:
    """Render an arbitrary Jinja template from the prompts directory."""
    return _jinja_env().get_template(template_name).render(**context)


def format_citations(chunks: list[RetrievedChunk]) -> list[Citation]:
    return [
        Citation(
            source_index=i,
            source_marker=f"S{i}",
            filename=c.metadata.filename,
            page=c.metadata.page,
            source_text=c.text.strip(),
            section=c.metadata.section,
            chunk_id=c.metadata.chunk_id,
        )
        for i, c in enumerate(chunks, start=1)
    ]


def answer(
    question: str,
    k: int | None = None,
    filters: dict[str, object] | None = None,
    collection_name: str | None = None,
) -> RagAnswer:
    abstract_requested = bool(_ABSTRACT_REQUEST.search(question))
    chunks = []
    if abstract_requested:
        chunks = _abstract_chunks(fetch_all_chunks(filters=filters, collection_name=collection_name))
    if not chunks:
        chunks = retrieve(question, k=k, filters=filters, collection_name=collection_name)
    return answer_from_chunks(question, chunks, abstract_requested=abstract_requested)


def answer_from_chunks(
    question: str, chunks: list[RetrievedChunk], *,
    selected_text: str | None = None, abstract_requested: bool = False,
) -> RagAnswer:
    """Generate a cited answer from explicit source context, including PDF pages."""
    if not chunks:
        return RagAnswer(
            question=question,
            answer="Tôi không có đủ thông tin trong ngữ cảnh được cung cấp để trả lời.",
        )

    prompt = render_prompt(
        ANSWER_TEMPLATE, question=question, chunks=chunks,
        abstract_requested=abstract_requested,
        selected_text=selected_text,
    )
    text = invoke_llm(prompt)

    return RagAnswer(
        question=question,
        answer=text.strip(),
        citations=format_citations(chunks),
        chunks=chunks,
    )

