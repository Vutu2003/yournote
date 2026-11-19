"""Retrieval, prompts, citations, and grounded answers."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import re
import hashlib
import time

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from src.config import settings
from src.filters import filters_to_qdrant
from src.llm import invoke_llm, llm_operation
from src.locks import index_operation
from src.schemas import ChunkMetadata, Citation, RagAnswer, RetrievedChunk, RetrievalTrace
from src.errors import LLMServiceError, LLMErrorCode
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


def _active(chunks):
    from src.documents import all_documents
    active={doc['filename']:doc for doc in all_documents()}
    return [chunk for chunk in chunks if (chunk.metadata.filename not in active and chunk.metadata.schema_version<2) or (
        chunk.metadata.filename in active and chunk.metadata.document_id==active[chunk.metadata.filename]['id'] and
        (chunk.metadata.document_version or active[chunk.metadata.filename].get('legacy_version'))==active[chunk.metadata.filename]['active_version'])]


@index_operation
def retrieve_vector(query, k=None, filters=None, collection_name=None):
    """Preserved baseline for evaluation; Qdrant receives scope before ranking."""
    store=get_vector_store(collection_name=collection_name)
    hits=store.similarity_search_with_score(query=query,k=k or settings.top_k,filter=filters_to_qdrant(filters))
    return _active([RetrievedChunk(text=doc.page_content,score=float(score),metadata=ChunkMetadata(**doc.metadata)) for doc,score in hits])


@index_operation
def retrieve(query,k=None,filters=None,collection_name=None):
    from src.retrieval import lexical_rank,reciprocal_rank_fusion
    count=k or settings.top_k
    candidates=min(128,max(12,count*4))
    vector=retrieve_vector(query,k=candidates,filters=filters,collection_name=collection_name)
    lexical=lexical_rank(query,fetch_all_chunks(filters=filters,collection_name=collection_name),candidates)
    return reciprocal_rank_fusion([vector,lexical],count)


@index_operation
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
            if len(results)>settings.retrieval_max_chunks:
                raise LLMServiceError(413, 'Selected material exceeds the retrieval limit. Choose fewer sources.')
    results.sort(
        key=lambda r: (
            r.metadata.filename,
            r.metadata.page or 0,
            int(r.metadata.chunk_id.rsplit(":", 1)[-1]),
        )
    )
    return _active(results)


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
        if all(chunk.metadata.page is None for chunk in document):
            selected.extend(chunk for chunk in document if 'abstract' in (chunk.metadata.section or '').casefold())
            continue
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
    from src.documents import get_document
    from src.grounding import verify_citation
    from src.locations import Locator
    result=[]
    for index,chunk in enumerate(chunks,1):
        meta=chunk.metadata
        doc=get_document(filename=meta.filename)
        version=meta.document_version or (doc['active_version'] if doc else None)
        citation=Citation(source_index=index,source_marker=f'S{index}',filename=meta.filename,page=meta.page,
            source_text=chunk.text.strip(),section=meta.section,chunk_id=meta.chunk_id,
            schema_version=2 if version else meta.schema_version,document_id=meta.document_id,
            document_version=version,locator=meta.locator or (Locator(kind='page',page=meta.page) if meta.page else None))
        if version and doc:
            try: verify_citation(citation)
            except ValueError: raise LLMServiceError.for_code(LLMErrorCode.INVALID_RESPONSE) from None
        result.append(citation)
    return result


@llm_operation
def answer(
    question: str,
    k: int | None = None,
    filters: dict[str, object] | None = None,
    collection_name: str | None = None,
    history: list[dict] | None = None,
) -> RagAnswer:
    from src.conversation import contextual_query
    started=time.monotonic()
    query=contextual_query(question,history or [])
    abstract_requested = bool(_ABSTRACT_REQUEST.search(question))
    chunks = []
    if abstract_requested:
        chunks = _abstract_chunks(fetch_all_chunks(filters=filters, collection_name=collection_name))
    if not chunks:
        chunks = retrieve(query, k=k, filters=filters, collection_name=collection_name)
    trace=RetrievalTrace(method='hybrid_bm25_rrf' if not abstract_requested else 'structural_or_hybrid',
        query_sha256=hashlib.sha256(query.encode()).hexdigest(),chunk_ids=[chunk.metadata.chunk_id for chunk in chunks],
        context_count=len(chunks),duration_ms=(time.monotonic()-started)*1000,history_turns=len(history or []))
    return answer_from_chunks(question,chunks,abstract_requested=abstract_requested,history=history,trace=trace)


@llm_operation
def answer_from_chunks(
    question: str, chunks: list[RetrievedChunk], *,
    selected_text: str | None = None, abstract_requested: bool = False,
    history: list[dict] | None = None, trace: RetrievalTrace | None = None,
) -> RagAnswer:
    """Generate a cited answer from explicit source context, including PDF pages."""
    if not chunks:
        return RagAnswer(
            question=question,
            answer="Tôi không có đủ thông tin trong ngữ cảnh được cung cấp để trả lời.",
            retrieval_trace=trace,
        )

    citations=format_citations(chunks)
    prompt = render_prompt(
        ANSWER_TEMPLATE, question=question, chunks=chunks,
        abstract_requested=abstract_requested,
        selected_text=selected_text, history=history or [],
    )
    text = invoke_llm(prompt)

    used=set(re.findall(r'\[(S[1-9][0-9]*)\]',text))
    valid={citation.source_marker for citation in citations}
    refusal='Tôi không có đủ thông tin trong ngữ cảnh được cung cấp để trả lời.'
    if not used<=valid or (not used and text.strip()!=refusal):
        raise LLMServiceError.for_code(LLMErrorCode.INVALID_RESPONSE)
    return RagAnswer(question=question,answer=text.strip(),citations=[c for c in citations if c.source_marker in used],
                     chunks=chunks,retrieval_trace=trace)

