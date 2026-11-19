"""Export learning outputs to JSON or Markdown."""

from __future__ import annotations

import html
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from src.locations import location_label
from src.schemas import Citation, FlashcardSet, QuizSet, RagAnswer, Summary, MindMap, MindMapNode

ExportFormat = Literal["text", "md", "json"]


def _citation_line(c: Citation) -> str:
    location=f'p.{c.page}' if c.page else location_label(c.locator)
    parts = [f"[{c.source_marker}] {html.escape(c.filename)} {html.escape(location)}"]
    if c.locator and c.locator.anchor: parts.append(f'anchor: {c.locator.anchor}')
    if c.document_version: parts.append(f'version: {c.document_version}')
    if c.section:
        parts.append(f"section: {html.escape(c.section)}")
    if c.chunk_id:
        parts.append(f"chunk: {c.chunk_id}")
    return " | ".join(parts)


def _details_block(summary: str, content: str) -> str:
    safe_summary = html.escape(summary, quote=False)
    safe_content = html.escape(content, quote=False)
    return (
        "<details>"
        f"<summary>{safe_summary}</summary>"
        f"<div style=\"margin:8px 0 0 0; white-space:pre-wrap;\">{safe_content}</div>"
        "</details>"
    )


def _citation_source_text_block(c: Citation) -> str:
    if not c.source_text:
        return ""
    return "\n  " + _details_block("Xem đoạn nguồn", c.source_text)


def _marker_details(citations: list[Citation], markers: list[str]) -> list[str]:
    by_marker = {c.source_marker: c for c in citations}
    lines: list[str] = []
    for m in markers:
        c = by_marker.get(m)
        if c is None:
            continue
        location=f'p.{c.page}' if c.page else location_label(c.locator)
        summary = f"[{c.source_marker}] {c.filename} {location}"
        if c.section:
            summary += f" | section: {c.section}"
        if c.chunk_id:
            summary += f" | chunk: {c.chunk_id}"
        if c.source_text:
            lines.append(f"- {_details_block(summary, c.source_text)}")
        else:
            lines.append(f"- {summary}")
    return lines


def _citations_block(citations: list[Citation]) -> str:
    if not citations:
        return ""
    lines = ["## Sources", ""]
    for c in citations:
        lines.append(f"- {_citation_line(c)}{_citation_source_text_block(c)}")
    return "\n".join(lines) + "\n"


def _render_with_sources(body_lines: list[str], citations: list[Citation]) -> str:
    lines = [*body_lines, ""]
    c = _citations_block(citations)
    if c:
        lines.append(c)
    return "\n".join(lines).rstrip() + "\n"


def _research_statement(statement):
    lines=[html.escape(statement.text,quote=False)]
    for ref in statement.evidence:
        lines.append(f'> [{ref.source_marker}] '+html.escape(ref.quote,quote=False).replace('\n','\n> '))
    return '\n\n'.join(lines)


def _research_markdown(model):
    from src.research_schemas import Comparison,KnowledgeGraph
    lines=['# '+html.escape(getattr(model,'title','Mạng tri thức' if isinstance(model,KnowledgeGraph) else 'So sánh tài liệu'),quote=False),'','## Mục tiêu','',html.escape(model.goal,quote=False),'','## Phạm vi nguồn','']
    for source in model.sources:
        lines.append(f'- {html.escape(source.filename)}: {len(source.examined_chunk_ids)}/{source.total_chunks} đoạn; {source.coverage}; version {source.document_version}')
    if isinstance(model,KnowledgeGraph):
        lines+=['','## Khái niệm','']
        for node in model.nodes:
            lines+=['### '+html.escape(node.label),'', 'Tên thay thế: '+', '.join(html.escape(a) for a in node.aliases),'',_research_statement(node.definition),'']
        nodes={node.id:node for node in model.nodes}
        lines+=['','## Quan hệ','']
        for edge in model.edges:
            lines+=['### '+html.escape(nodes[edge.source].label)+' → '+html.escape(nodes[edge.target].label)+' ('+edge.relation+')','',_research_statement(edge.statement),'']
    elif isinstance(model,Comparison):
        for criterion in model.criteria:
            lines+=['','## '+html.escape(criterion.label),'']
            for source in criterion.sources:
                lines+=['### '+html.escape(source.filename),'',_research_statement(source.statement) if source.statement else 'Chưa tìm thấy trong các đoạn đã xét: '+html.escape(source.limitation)]
            for finding in model.findings:
                if finding.criterion_id==criterion.id: lines+=['','### '+finding.kind,'',_research_statement(finding.statement)]
    else:
        for section in model.sections:
            lines+=['','## '+html.escape(section.title),'']
            lines.extend(_research_statement(statement)+'\n' for statement in section.statements)
    if hasattr(model,'conclusion'): lines+=['','## Kết luận','']
    lines.extend(_research_statement(statement)+'\n' for statement in getattr(model,'conclusion',[]))
    lines+=['','## Giới hạn','']+['- '+html.escape(limit,quote=False) for limit in model.limits]
    lines.extend('- '+html.escape(note.filename)+': '+html.escape(note.detail) for note in model.source_notes)
    return _render_with_sources(lines,model.citations)


def _to_markdown(model: BaseModel) -> str:
    from src.research_schemas import Comparison,StudyReport,KnowledgeGraph
    if isinstance(model,(Comparison,StudyReport,KnowledgeGraph)): return _research_markdown(model)
    if isinstance(model, MindMap):
        lines = [f"# Sơ đồ tư duy: {model.root.label}", ""]

        def walk(node: MindMapNode, depth: int):
            indent = "  " * depth
            markers = " ".join(f"[{marker}]" for marker in node.source_markers)
            lines.append(f"{indent}- **{node.label}** {markers}")
            if node.description:
                lines.append(f"{indent}  {node.description}")
            for child in node.children:
                walk(child, depth + 1)

        walk(model.root, 0)
        return _render_with_sources(lines, model.citations)

    if isinstance(model, Summary):
        title = "# Summary" + (f": {model.target}" if model.target else "")
        lines: list[str] = [title, "", f"_Scope: {model.scope}_", ""]
        if model.summary:
            lines.extend([model.summary.strip(), ""])
        if model.key_points:
            lines.extend(["## Key Points", "", *[f"- {kp}" for kp in model.key_points], ""])
        return _render_with_sources(lines, model.citations)

    if isinstance(model, RagAnswer):
        return _render_with_sources([model.answer.strip()], model.citations)

    if isinstance(model, QuizSet):
        title = "# Quiz" + (f": {model.target}" if model.target else "")
        lines = [title, "", f"_Scope: {model.scope} | Items: {len(model.items)}_", ""]
        for idx, item in enumerate(model.items, start=1):
            meta_parts: list[str] = []
            if item.topic:
                meta_parts.append(f"topic: {item.topic}")
            if item.difficulty:
                meta_parts.append(f"difficulty: {item.difficulty}")
            meta_suffix = f" _({' | '.join(meta_parts)})_" if meta_parts else ""

            lines.extend([f"## Q{idx}.{meta_suffix}", "", item.question.strip(), ""])
            for opt_idx, option in enumerate(item.options):
                lines.append(f"- {chr(ord('A') + opt_idx)}) {option}")
            lines.append("")
            lines.append(f"**Answer:** {chr(ord('A') + item.correct_index)}")
            if item.explanation:
                lines.append(f"**Explanation:** {item.explanation.strip()}")
            if item.source_markers:
                lines.extend(["**Sources:**", *_marker_details(model.citations, item.source_markers)])
            lines.append("")

        c = _citations_block(model.citations)
        if c:
            lines.append(c)
        return "\n".join(lines).rstrip() + "\n"

    if isinstance(model, FlashcardSet):
        title = "# Flashcards" + (f": {model.target}" if model.target else "")
        lines = [title, "", f"_Scope: {model.scope} | Cards: {len(model.cards)}_", ""]
        for idx, card in enumerate(model.cards, start=1):
            topic = f" — {card.topic}" if card.topic else ""
            lines.extend([f"## Card {idx}{topic}", ""])
            lines.append(f"**Front:** {card.front.strip()}")
            lines.append(f"**Back:** {card.back.strip()}")
            if card.hint:
                lines.append(f"**Hint:** {card.hint.strip()}")
            if card.source_markers:
                lines.extend(["**Sources:**", *_marker_details(model.citations, card.source_markers)])
            lines.append("")

        c = _citations_block(model.citations)
        if c:
            lines.append(c)
        return "\n".join(lines).rstrip() + "\n"

    raise TypeError(f"Unsupported model type: {type(model).__name__}")


def export(
    model: BaseModel, *, fmt: ExportFormat = "text", output: Path | None = None
) -> str | Path:
    """Render model to a string, optionally writing it to disk.

    Args: model, fmt, output (optional).
    Returns: rendered string if output is None; otherwise the written path.
    Raises: TypeError for unsupported model type; ValueError for unknown fmt.
    """
    if fmt == "json":
        text = model.model_dump_json(indent=2) + "\n"
    elif fmt in {"text", "md"}:
        text = _to_markdown(model)
    else:
        raise ValueError(f"Unknown fmt '{fmt}'. Expected 'text' | 'md' | 'json'.")

    if output is None:
        return text

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8")
    return output

