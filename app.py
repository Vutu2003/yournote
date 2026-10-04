"""Gradio workspace for source-grounded document learning."""

from __future__ import annotations

import html
import re
from pathlib import Path
from typing import Any

import gradio as gr
from loguru import logger

from src.config import settings
from src.export import export
from src.filters import MetadataFilter, filters_to_dict
from src.indexing import save_and_ingest_pdf
from src.learning import generate_flashcards, generate_quiz, summarize
from src.llm import set_runtime_gemini_api_key
from src.rag import answer
from src.schemas import Citation, FlashcardSet, QuizSet, RagAnswer, Summary
from src.store import list_documents

_CSS = Path("static/style.css").read_text(encoding="utf-8")
_ALL_PAGES = "(Tất cả trang)"
_DEBUG_QA = "Trò chuyện"
_DEBUG_SUMMARY = "Tóm tắt"
_DEBUG_QUIZ = "Quiz"
_DEBUG_FLASHCARDS = "Flashcards"
_MARKER_PATTERN = re.compile(r"\[(S\d+)\]")


def _safe(value: object) -> str:
    return html.escape(str(value or ""), quote=True)


def _paragraphs(text: str) -> str:
    paragraphs = [part.strip() for part in text.split("\n\n") if part.strip()]
    return "".join(f'<p>{_safe(part).replace(chr(10), "<br>")}</p>' for part in paragraphs)


def _read_uploaded_pdf(file_obj: object) -> tuple[bytes, str]:
    """Normalize a Gradio file payload into PDF bytes and its filename."""
    if isinstance(file_obj, str):
        path = Path(file_obj)
        return path.read_bytes(), path.name

    path = getattr(file_obj, "path", None)
    orig_name = getattr(file_obj, "orig_name", None)
    if isinstance(path, str) and path:
        upload_path = Path(path)
        name = str(orig_name).strip() if isinstance(orig_name, str) and orig_name.strip() else upload_path.name
        return upload_path.read_bytes(), name

    if isinstance(file_obj, dict):
        path = file_obj.get("path")
        name = file_obj.get("orig_name") or file_obj.get("name")
        if isinstance(path, str) and path:
            upload_path = Path(path)
            return upload_path.read_bytes(), str(name).strip() if name else upload_path.name

    raise TypeError(f"Unsupported uploaded file type: {type(file_obj).__name__}")


def _read_uploaded_pdfs(file_obj: object) -> list[tuple[bytes, str]]:
    if file_obj is None:
        return []
    if isinstance(file_obj, (list, tuple)):
        return [_read_uploaded_pdf(item) for item in file_obj]
    return [_read_uploaded_pdf(file_obj)]


def _filters(filenames: list[str] | None, page: str | None) -> dict[str, object] | None:
    payload: dict[str, object] = {}
    if filenames:
        payload["filenames"] = filenames
    if page and page != _ALL_PAGES and len(filenames or []) == 1:
        payload["page"] = int(page)
    return filters_to_dict(MetadataFilter.model_validate(payload)) if payload else None


def _page_update(doc_map: dict[str, Any], selected: list[str], current_page: str = _ALL_PAGES) -> dict[str, Any]:
    if len(selected) != 1:
        return gr.update(choices=[_ALL_PAGES], value=_ALL_PAGES, interactive=False)
    pages = (doc_map.get(selected[0]) or {}).get("pages") or []
    choices = [_ALL_PAGES, *[str(value) for value in pages]]
    return gr.update(choices=choices, value=current_page if current_page in choices else _ALL_PAGES, interactive=True)


def _refresh_docs(
    selected_docs: list[str] | None = None,
    current_page: str = _ALL_PAGES,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], str, str]:
    documents = list_documents()
    choices = [item["filename"] for item in documents]
    doc_map = {item["filename"]: item for item in documents}
    selected = [name for name in (selected_docs or []) if name in doc_map]
    count = sum(int(item["chunk_count"]) for item in documents)
    summary = f"{len(documents)} tài liệu đã index · {count} đoạn" if documents else "Chưa có tài liệu được index."
    return (
        gr.update(choices=choices, value=selected),
        doc_map,
        _page_update(doc_map, selected, current_page),
        summary,
        f"Đã chọn {len(selected)} nguồn",
    )


def _load_docs() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], str, str]:
    return _refresh_docs()


def _selection_change(doc_map: dict[str, Any], selected: list[str]) -> tuple[dict[str, Any], str]:
    selected = selected or []
    return _page_update(doc_map or {}, selected), f"Đã chọn {len(selected)} nguồn"


def _upload_pdf(
    file_obj: object | None,
    selected_docs: list[str],
    current_page: str,
) -> tuple[str, dict[str, Any], dict[str, Any], dict[str, Any], str, str]:
    try:
        payloads = _read_uploaded_pdfs(file_obj)
    except Exception as exc:
        logger.error("PDF upload preparation failed: {}", type(exc).__name__)
        return ("Không thể đọc PDF. Vui lòng thử lại.", *_refresh_docs(selected_docs, current_page))

    if not payloads:
        return ("Vui lòng chọn PDF.", *_refresh_docs(selected_docs, current_page))

    successes = 0
    failures = 0
    for file_bytes, filename in payloads:
        try:
            save_and_ingest_pdf(file_bytes, filename)
            successes += 1
        except Exception as exc:
            failures += 1
            logger.error("PDF indexing failed ({}): {}", type(exc).__name__, _safe(filename))

    if successes and not failures:
        status = f"Đã index {successes} tài liệu."
    elif successes:
        status = f"Đã index {successes} tài liệu; {failures} tài liệu không thành công."
    else:
        status = "Không thể index PDF. Vui lòng thử lại."
    return (status, *_refresh_docs(selected_docs, current_page))


def _source_group(
    citations: list[Citation],
    title: str,
    markers: list[str] | None = None,
    include_text: bool = True,
) -> str:
    if markers is not None:
        by_marker = {item.source_marker: item for item in citations}
        chosen = [by_marker[marker] for marker in dict.fromkeys(markers) if marker in by_marker]
    else:
        chosen = citations
    if not chosen:
        return ""
    rows: list[str] = []
    for item in chosen:
        label = f"[{item.source_marker}] {item.filename} · tr. {item.page}"
        details = []
        if include_text and item.chunk_id:
            details.append(f'<div class="source-meta">Mã đoạn: {_safe(item.chunk_id)}</div>')
        if include_text and item.section:
            details.append(f'<div class="source-meta">Mục: {_safe(item.section)}</div>')
        if include_text and item.source_text:
            details.append(f'<div class="source-text">{_safe(item.source_text)}</div>')
        if details:
            rows.append(
                '<details class="source-item"><summary>'
                + _safe(label)
                + '</summary><div class="source-item-body">'
                + "".join(details)
                + "</div></details>"
            )
        else:
            rows.append(f'<div class="source-line">{_safe(label)}</div>')
    return (
        f'<details class="source-group"><summary>{_safe(title)} ({len(chosen)})</summary>'
        f'<div class="source-list">{"".join(rows)}</div></details>'
    )


def _render_answer(result: RagAnswer) -> str:
    markers = _MARKER_PATTERN.findall(result.answer)
    cited = _source_group(result.citations, "Nguồn tham chiếu", markers) if markers else ""
    remaining = [item for item in result.citations if item.source_marker not in set(markers)]
    retrieved = _source_group(remaining, "Nguồn đã truy xuất")
    return '<div class="answer-body">' + _paragraphs(result.answer) + cited + retrieved + "</div>"


def _render_summary(result: Summary) -> str:
    points = "".join(f"<li>{_safe(item)}</li>" for item in result.key_points)
    key_points = f'<h3>Ý chính</h3><ul class="key-points">{points}</ul>' if points else ""
    return (
        '<div class="studio-result"><h3>Tóm tắt</h3>'
        + _paragraphs(result.summary)
        + key_points
        + _source_group(result.citations, "Nguồn đã sử dụng", include_text=False)
        + "</div>"
    )


def _write_export(markdown: str, filename: str) -> str:
    path = Path("exports") / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown, encoding="utf-8")
    return str(path)


def _debug_update(
    debug_state: dict[str, str] | None,
    name: str,
    raw_json: str,
    selected: str,
) -> tuple[dict[str, str], str]:
    updated = dict(debug_state or {})
    updated[name] = raw_json
    return updated, updated.get(selected, "")


def _show_debug(selected: str, debug_state: dict[str, str] | None) -> str:
    return (debug_state or {}).get(selected, "")


def _ask_chat(
    message: str,
    history: list[dict[str, str]] | None,
    k: int,
    selected_docs: list[str] | None,
    page: str,
    gemini_key: str,
    debug_state: dict[str, str] | None,
    debug_selected: str,
) -> tuple[list[dict[str, str]], str, str, dict[str, str], str]:
    prior = list(history or [])
    question = (message or "").strip()
    current_debug = dict(debug_state or {})
    if not question:
        return prior, message or "", "Vui lòng nhập câu hỏi.", current_debug, current_debug.get(debug_selected, "")
    if not selected_docs:
        return prior, message, "Vui lòng chọn ít nhất một tài liệu.", current_debug, current_debug.get(debug_selected, "")
    try:
        set_runtime_gemini_api_key(gemini_key)
        result = answer(question, k=int(k), filters=_filters(selected_docs, page))
        rendered = _render_answer(result)
        raw = result.model_dump_json(indent=2)
    except Exception as exc:
        logger.error("Q&A generation failed: {}", type(exc).__name__)
        return prior, message, "Không thể tạo câu trả lời. Vui lòng thử lại.", current_debug, current_debug.get(debug_selected, "")
    prior.extend([{"role": "user", "content": _safe(question)}, {"role": "assistant", "content": rendered}])
    updated, visible_debug = _debug_update(current_debug, _DEBUG_QA, raw, debug_selected)
    status = "Không tìm thấy đủ thông tin trong nguồn đã chọn." if not result.citations else ""
    return prior, "", status, updated, visible_debug


def _generate_summary(
    query: str,
    k: int,
    selected_docs: list[str] | None,
    page: str,
    gemini_key: str,
    debug_state: dict[str, str] | None,
    debug_selected: str,
    progress: gr.Progress = gr.Progress(),
) -> tuple[Any, Any, str, dict[str, str], str]:
    current_debug = dict(debug_state or {})
    if not selected_docs:
        return gr.update(), gr.update(), "Vui lòng chọn ít nhất một tài liệu.", current_debug, current_debug.get(debug_selected, "")
    try:
        set_runtime_gemini_api_key(gemini_key)
        progress(0.3, desc="Đang truy xuất ngữ cảnh…")
        result = summarize(query=(query or "").strip() or None, k=int(k), filters=_filters(selected_docs, page))
        progress(0.9, desc="Đang chuẩn bị kết quả…")
        rendered = _render_summary(result)
        download = _write_export(export(result, fmt="md"), "summary.md")
        updated, visible_debug = _debug_update(current_debug, _DEBUG_SUMMARY, result.model_dump_json(indent=2), debug_selected)
        return rendered, gr.update(value=download, visible=True), "", updated, visible_debug
    except Exception as exc:
        logger.error("Summary generation failed: {}", type(exc).__name__)
        return gr.update(), gr.update(), "Không thể tạo nội dung. Vui lòng thử lại.", current_debug, current_debug.get(debug_selected, "")


def _quiz_view(state: dict[str, Any]) -> tuple[str, dict[str, Any], str, str, dict[str, Any], dict[str, Any]]:
    result = QuizSet.model_validate(state["result"])
    index = int(state["index"])
    item = result.items[index]
    question = f'<div class="viewer-count">Câu {index + 1} / {len(result.items)}</div><div class="viewer-question">{_safe(item.question)}</div>'
    options = [(f"{chr(65 + option_index)}. {option}", str(option_index)) for option_index, option in enumerate(item.options)]
    return (
        question,
        gr.update(choices=options, value=None),
        "",
        "",
        gr.update(interactive=index > 0),
        gr.update(interactive=index < len(result.items) - 1),
    )


def _generate_quiz(
    query: str,
    count: int,
    k: int,
    selected_docs: list[str] | None,
    page: str,
    gemini_key: str,
    debug_state: dict[str, str] | None,
    debug_selected: str,
    progress: gr.Progress = gr.Progress(),
) -> tuple[Any, Any, Any, Any, Any, Any, Any, Any, Any, str, dict[str, str], str]:
    current_debug = dict(debug_state or {})
    unchanged = (gr.update(),) * 9
    if not selected_docs:
        return (*unchanged, "Vui lòng chọn ít nhất một tài liệu.", current_debug, current_debug.get(debug_selected, ""))
    try:
        set_runtime_gemini_api_key(gemini_key)
        progress(0.3, desc="Đang truy xuất ngữ cảnh…")
        result = generate_quiz(query=(query or "").strip() or None, count=int(count), k=int(k), filters=_filters(selected_docs, page))
        if not result.items:
            raise ValueError("Empty quiz")
        progress(0.9, desc="Đang chuẩn bị câu hỏi…")
        state = {"result": result.model_dump(), "index": 0, "revealed": False}
        download = _write_export(export(result, fmt="md"), "quiz.md")
        updated, visible_debug = _debug_update(current_debug, _DEBUG_QUIZ, result.model_dump_json(indent=2), debug_selected)
        return (state, gr.update(visible=True), *_quiz_view(state), gr.update(value=download, visible=True), "", updated, visible_debug)
    except Exception as exc:
        logger.error("Quiz generation failed: {}", type(exc).__name__)
        return (*unchanged, "Không thể tạo nội dung. Vui lòng thử lại.", current_debug, current_debug.get(debug_selected, ""))


def _check_quiz(state: dict[str, Any] | None, selected_option: str | None) -> tuple[dict[str, Any], Any, Any, str]:
    if not state or not state.get("result"):
        return state or {}, gr.update(), gr.update(), "Hãy tạo quiz trước."
    if selected_option is None:
        return state, gr.update(), gr.update(), "Vui lòng chọn một đáp án."
    result = QuizSet.model_validate(state["result"])
    item = result.items[int(state["index"])]
    try:
        chosen = int(selected_option)
    except (TypeError, ValueError):
        return state, gr.update(), gr.update(), "Vui lòng chọn một đáp án."
    if not 0 <= chosen < len(item.options):
        return state, gr.update(), gr.update(), "Vui lòng chọn một đáp án."
    updated = dict(state, revealed=True)
    verdict = "Chính xác." if chosen == item.correct_index else "Chưa đúng."
    correct = f"{chr(65 + item.correct_index)}. {item.options[item.correct_index]}"
    feedback = f'<div class="answer-feedback"><strong>{_safe(verdict)}</strong><p>Đáp án: {_safe(correct)}</p>{_paragraphs(item.explanation)}</div>'
    sources = _source_group(result.citations, "Nguồn tham chiếu", item.source_markers)
    return updated, feedback, sources, ""


def _move_quiz(state: dict[str, Any] | None, step: int) -> tuple[Any, Any, Any, Any, Any, Any, Any, str]:
    if not state or not state.get("result"):
        return (gr.update(),) * 7 + ("Hãy tạo quiz trước.",)
    result = QuizSet.model_validate(state["result"])
    index = max(0, min(len(result.items) - 1, int(state["index"]) + step))
    updated = dict(state, index=index, revealed=False)
    return (updated, *_quiz_view(updated), "")


def _quiz_prev(state: dict[str, Any] | None) -> tuple[Any, Any, Any, Any, Any, Any, Any, str]:
    return _move_quiz(state, -1)


def _quiz_next(state: dict[str, Any] | None) -> tuple[Any, Any, Any, Any, Any, Any, Any, str]:
    return _move_quiz(state, 1)


def _flash_view(state: dict[str, Any]) -> tuple[str, str, str, dict[str, Any], dict[str, Any], dict[str, Any]]:
    result = FlashcardSet.model_validate(state["result"])
    index = int(state["index"])
    card = result.cards[index]
    title = f'<div class="viewer-count">Thẻ {index + 1} / {len(result.cards)}</div>'
    front = f'<div class="flash-face"><div class="face-label">Mặt trước</div>{_paragraphs(card.front)}</div>'
    return (
        title + front,
        "",
        "",
        gr.update(interactive=index > 0),
        gr.update(interactive=index < len(result.cards) - 1),
        gr.update(interactive=True),
    )


def _generate_flashcards(
    query: str,
    count: int,
    k: int,
    selected_docs: list[str] | None,
    page: str,
    gemini_key: str,
    debug_state: dict[str, str] | None,
    debug_selected: str,
    progress: gr.Progress = gr.Progress(),
) -> tuple[Any, Any, Any, Any, Any, Any, Any, Any, Any, str, dict[str, str], str]:
    current_debug = dict(debug_state or {})
    unchanged = (gr.update(),) * 9
    if not selected_docs:
        return (*unchanged, "Vui lòng chọn ít nhất một tài liệu.", current_debug, current_debug.get(debug_selected, ""))
    try:
        set_runtime_gemini_api_key(gemini_key)
        progress(0.3, desc="Đang truy xuất ngữ cảnh…")
        result = generate_flashcards(query=(query or "").strip() or None, count=int(count), k=int(k), filters=_filters(selected_docs, page))
        if not result.cards:
            raise ValueError("Empty flashcard set")
        progress(0.9, desc="Đang chuẩn bị thẻ…")
        state = {"result": result.model_dump(), "index": 0, "revealed": False}
        download = _write_export(export(result, fmt="md"), "flashcards.md")
        updated, visible_debug = _debug_update(current_debug, _DEBUG_FLASHCARDS, result.model_dump_json(indent=2), debug_selected)
        return (state, gr.update(visible=True), *_flash_view(state), gr.update(value=download, visible=True), "", updated, visible_debug)
    except Exception as exc:
        logger.error("Flashcards generation failed: {}", type(exc).__name__)
        return (*unchanged, "Không thể tạo nội dung. Vui lòng thử lại.", current_debug, current_debug.get(debug_selected, ""))


def _reveal_flashcard(state: dict[str, Any] | None) -> tuple[dict[str, Any], Any, Any, Any, str]:
    if not state or not state.get("result"):
        return state or {}, gr.update(), gr.update(), gr.update(), "Hãy tạo flashcards trước."
    result = FlashcardSet.model_validate(state["result"])
    card = result.cards[int(state["index"])]
    updated = dict(state, revealed=True)
    hint = f'<p class="card-hint">Gợi ý: {_safe(card.hint)}</p>' if card.hint else ""
    back = f'<div class="flash-face flash-back"><div class="face-label">Mặt sau</div>{_paragraphs(card.back)}{hint}</div>'
    sources = _source_group(result.citations, "Nguồn tham chiếu", card.source_markers)
    return updated, back, sources, gr.update(interactive=False), ""


def _move_flashcard(state: dict[str, Any] | None, step: int) -> tuple[Any, Any, Any, Any, Any, Any, Any, str]:
    if not state or not state.get("result"):
        return (gr.update(),) * 7 + ("Hãy tạo flashcards trước.",)
    result = FlashcardSet.model_validate(state["result"])
    index = max(0, min(len(result.cards) - 1, int(state["index"]) + step))
    updated = dict(state, index=index, revealed=False)
    return (updated, *_flash_view(updated), "")


def _flash_prev(state: dict[str, Any] | None) -> tuple[Any, Any, Any, Any, Any, Any, Any, str]:
    return _move_flashcard(state, -1)


def _flash_next(state: dict[str, Any] | None) -> tuple[Any, Any, Any, Any, Any, Any, Any, str]:
    return _move_flashcard(state, 1)


_theme = gr.themes.Base().set(
    background_fill_primary="#f6f7f9",
    background_fill_secondary="#f1f3f6",
    block_background_fill="#ffffff",
    block_border_color="#e2e6eb",
    input_background_fill="#ffffff",
)

_initial_documents = list_documents()
_initial_doc_choices = [str(item["filename"]) for item in _initial_documents]
_initial_doc_map = {str(item["filename"]): item for item in _initial_documents}
_initial_chunk_count = sum(int(item["chunk_count"]) for item in _initial_documents)
_initial_doc_summary = (
    f"{len(_initial_documents)} tài liệu đã index · {_initial_chunk_count} đoạn"
    if _initial_documents else "Chưa có tài liệu được index."
)

with gr.Blocks(title="Research Notebook", fill_width=True, fill_height=True) as demo:
    with gr.Row(elem_classes="app-header"):
        gr.HTML('<div class="brand-title">Research Notebook</div><div class="brand-subtitle">Khám phá và học từ tài liệu của bạn</div>')

    doc_map_state = gr.State(_initial_doc_map)
    debug_state = gr.State({})
    quiz_state = gr.State({})
    flash_state = gr.State({})

    with gr.Row(elem_classes="workspace"):
        with gr.Column(scale=3, min_width=240, elem_classes="sources-panel"):
            gr.HTML('<h2 class="panel-title">Nguồn tài liệu</h2>')
            upload = gr.File(label="Chọn PDF", file_types=[".pdf"], file_count="multiple", type="filepath", height=118, elem_classes="source-upload")
            upload_btn = gr.Button("Thêm PDF", variant="primary", elem_classes="primary-action")
            upload_status = gr.Markdown("", elem_classes="panel-status")
            with gr.Row(elem_classes="source-toolbar"):
                doc_summary = gr.Markdown(_initial_doc_summary, elem_classes="doc-summary")
                refresh_btn = gr.Button("↻", size="sm", scale=0, min_width=36, elem_classes="refresh-btn")
            docs = gr.CheckboxGroup(label="Tài liệu đã index", choices=_initial_doc_choices, value=[], elem_classes="document-list")
            selected_summary = gr.Markdown("Đã chọn 0 nguồn", elem_classes="selected-summary")
            page = gr.Dropdown(label="Trang", choices=[_ALL_PAGES], value=_ALL_PAGES, interactive=False)

        with gr.Column(scale=6, min_width=450, elem_classes="chat-panel"):
            gr.HTML('<h2 class="panel-title">Trò chuyện</h2>')
            chatbot = gr.Chatbot(label="Hội thoại", show_label=False, height=540, sanitize_html=False, elem_classes="chat-history")
            chat_status = gr.Markdown("", elem_classes="panel-status")
            with gr.Row(elem_classes="chat-composer"):
                question = gr.Textbox(label="Hỏi tài liệu", placeholder="Hỏi về các nguồn đã chọn…", lines=1, scale=8, elem_classes="question-input")
                send_btn = gr.Button("Gửi", variant="primary", scale=1, min_width=72, elem_classes="send-btn")

        with gr.Column(scale=4, min_width=310, elem_classes="studio-panel"):
            gr.HTML('<h2 class="panel-title">Studio</h2>')
            with gr.Tabs(elem_classes="studio-tabs"):
                with gr.Tab("Tóm tắt"):
                    summary_query = gr.Textbox(label="Chủ đề (tuỳ chọn)", lines=1)
                    summary_btn = gr.Button("Tạo tóm tắt", variant="primary", elem_classes="primary-action")
                    summary_status = gr.Markdown("", elem_classes="panel-status")
                    summary_view = gr.HTML("", elem_classes="studio-output")
                    summary_download = gr.File(label="Tải Markdown", interactive=False, visible=False)

                with gr.Tab("Quiz"):
                    quiz_query = gr.Textbox(label="Chủ đề (tuỳ chọn)", lines=1)
                    quiz_count = gr.Slider(1, 30, value=3, step=1, label="Số câu hỏi")
                    quiz_btn = gr.Button("Tạo quiz", variant="primary", elem_classes="primary-action")
                    quiz_status = gr.Markdown("", elem_classes="panel-status")
                    with gr.Column(visible=False, elem_classes="quiz-viewer") as quiz_viewer:
                        quiz_question = gr.HTML("", elem_classes="viewer-question-block")
                        quiz_options = gr.Radio(label="Chọn đáp án", choices=[], value=None)
                        quiz_check = gr.Button("Kiểm tra đáp án")
                        quiz_feedback = gr.HTML("", elem_classes="viewer-feedback")
                        quiz_sources = gr.HTML("", elem_classes="viewer-sources")
                        with gr.Row(elem_classes="viewer-nav"):
                            quiz_prev = gr.Button("Câu trước", interactive=False)
                            quiz_next = gr.Button("Câu tiếp theo", interactive=False)
                    quiz_download = gr.File(label="Tải Markdown", interactive=False, visible=False)

                with gr.Tab("Flashcards"):
                    flash_query = gr.Textbox(label="Chủ đề (tuỳ chọn)", lines=1)
                    flash_count = gr.Slider(1, 40, value=3, step=1, label="Số thẻ")
                    flash_btn = gr.Button("Tạo thẻ", variant="primary", elem_classes="primary-action")
                    flash_status = gr.Markdown("", elem_classes="panel-status")
                    with gr.Column(visible=False, elem_classes="flash-viewer") as flash_viewer:
                        flash_front = gr.HTML("", elem_classes="flash-front")
                        flash_reveal = gr.Button("Hiển thị đáp án")
                        flash_back = gr.HTML("", elem_classes="flash-answer")
                        flash_sources = gr.HTML("", elem_classes="viewer-sources")
                        with gr.Row(elem_classes="viewer-nav"):
                            flash_prev = gr.Button("Thẻ trước", interactive=False)
                            flash_next = gr.Button("Thẻ tiếp theo", interactive=False)
                    flash_download = gr.File(label="Tải Markdown", interactive=False, visible=False)

    with gr.Accordion("Nâng cao / Debug", open=False, elem_classes="advanced-panel"):
        gr.Markdown(f"Gemini: `{settings.llm_model}` · Embedding: `{settings.embedding_model}` · Qdrant: `{settings.qdrant_collection}`")
        gemini_key = gr.Textbox(label="Gemini API Key (tuỳ chọn)", type="password", placeholder="Để trống để dùng cấu hình máy chủ", lines=1)
        with gr.Row():
            ask_k = gr.Slider(1, 32, value=6, step=1, label="Số đoạn truy xuất cho trò chuyện (k)")
            summary_k = gr.Slider(1, 64, value=10, step=1, label="Số đoạn truy xuất cho tóm tắt (k)")
            quiz_k = gr.Slider(1, 64, value=10, step=1, label="Số đoạn truy xuất cho quiz (k)")
            flash_k = gr.Slider(1, 64, value=16, step=1, label="Số đoạn truy xuất cho thẻ (k)")
        debug_select = gr.Dropdown(
            choices=[_DEBUG_QA, _DEBUG_SUMMARY, _DEBUG_QUIZ, _DEBUG_FLASHCARDS],
            value=_DEBUG_QA,
            label="Xem JSON của tính năng",
        )
        debug_json = gr.Code(label="Dữ liệu JSON", language="json", interactive=False)

    refresh_btn.click(fn=_refresh_docs, inputs=[docs, page], outputs=[docs, doc_map_state, page, doc_summary, selected_summary])
    docs.change(fn=_selection_change, inputs=[doc_map_state, docs], outputs=[page, selected_summary])
    upload_btn.click(
        fn=_upload_pdf,
        inputs=[upload, docs, page],
        outputs=[upload_status, docs, doc_map_state, page, doc_summary, selected_summary],
    )

    chat_inputs = [question, chatbot, ask_k, docs, page, gemini_key, debug_state, debug_select]
    chat_outputs = [chatbot, question, chat_status, debug_state, debug_json]
    question.submit(fn=_ask_chat, inputs=chat_inputs, outputs=chat_outputs)
    send_btn.click(fn=_ask_chat, inputs=chat_inputs, outputs=chat_outputs)

    summary_btn.click(
        fn=_generate_summary,
        inputs=[summary_query, summary_k, docs, page, gemini_key, debug_state, debug_select],
        outputs=[summary_view, summary_download, summary_status, debug_state, debug_json],
    )
    quiz_btn.click(
        fn=_generate_quiz,
        inputs=[quiz_query, quiz_count, quiz_k, docs, page, gemini_key, debug_state, debug_select],
        outputs=[quiz_state, quiz_viewer, quiz_question, quiz_options, quiz_feedback, quiz_sources, quiz_prev, quiz_next, quiz_download, quiz_status, debug_state, debug_json],
    )
    quiz_check.click(fn=_check_quiz, inputs=[quiz_state, quiz_options], outputs=[quiz_state, quiz_feedback, quiz_sources, quiz_status])
    quiz_prev.click(fn=_quiz_prev, inputs=[quiz_state], outputs=[quiz_state, quiz_question, quiz_options, quiz_feedback, quiz_sources, quiz_prev, quiz_next, quiz_status])
    quiz_next.click(fn=_quiz_next, inputs=[quiz_state], outputs=[quiz_state, quiz_question, quiz_options, quiz_feedback, quiz_sources, quiz_prev, quiz_next, quiz_status])

    flash_btn.click(
        fn=_generate_flashcards,
        inputs=[flash_query, flash_count, flash_k, docs, page, gemini_key, debug_state, debug_select],
        outputs=[flash_state, flash_viewer, flash_front, flash_back, flash_sources, flash_prev, flash_next, flash_reveal, flash_download, flash_status, debug_state, debug_json],
    )
    flash_reveal.click(fn=_reveal_flashcard, inputs=[flash_state], outputs=[flash_state, flash_back, flash_sources, flash_reveal, flash_status])
    flash_prev.click(fn=_flash_prev, inputs=[flash_state], outputs=[flash_state, flash_front, flash_back, flash_sources, flash_prev, flash_next, flash_reveal, flash_status])
    flash_next.click(fn=_flash_next, inputs=[flash_state], outputs=[flash_state, flash_front, flash_back, flash_sources, flash_prev, flash_next, flash_reveal, flash_status])
    debug_select.change(fn=_show_debug, inputs=[debug_select, debug_state], outputs=[debug_json])

if __name__ == "__main__":
    demo.queue(default_concurrency_limit=2).launch(css=_CSS, theme=_theme)
