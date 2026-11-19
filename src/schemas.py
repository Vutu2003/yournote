"""Pydantic schemas for chunks, answers, and learning outputs."""

from __future__ import annotations

from typing import Annotated, Literal
from src.locations import Locator, checked_page

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints, model_validator


class MindMapNode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
    description: Annotated[str, StringConstraints(strip_whitespace=True, max_length=1000)] = ""
    source_markers: list[Annotated[str, Field(pattern=r"^S[1-9][0-9]*$")]] = Field(default_factory=list, max_length=16)
    children: list["MindMapNode"] = Field(default_factory=list, max_length=8)


def validate_mindmap_tree(root: MindMapNode) -> MindMapNode:
    pending, count = [(root, 1)], 0
    while pending:
        node, depth = pending.pop()
        count += 1
        if depth > 4 or count > 65:
            raise ValueError("Mind map must have at most 4 levels and 65 nodes")
        pending.extend((child, depth + 1) for child in node.children)
    return root


MindMapTree = Annotated[MindMapNode, AfterValidator(validate_mindmap_tree)]


class ChunkMetadata(BaseModel):
    """Stable metadata attached to every chunk stored in Qdrant."""

    document_id: str
    filename: str
    source: str
    page: int | None = None
    chunk_id: str
    section: str | None = None
    schema_version: int = 1
    document_version: str | None = Field(default=None, pattern=r'^[a-f0-9]{64}$')
    locator: Locator | None = None

    @model_validator(mode='after')
    def location_matches_page(self):
        self.page = checked_page(self.page,self.locator)
        return self


class RetrievedChunk(BaseModel):
    """A retrieved chunk with its score and metadata."""

    text: str
    score: float
    metadata: ChunkMetadata


class Citation(BaseModel):
    """Citation extracted from a retrieved chunk's metadata."""

    source_index: int
    source_marker: str
    filename: str
    document_id: str | None = None
    page: int | None = None
    source_text: str | None = None
    section: str | None = None
    schema_version: int = 1
    document_version: str | None = Field(default=None, pattern=r'^[a-f0-9]{64}$')
    locator: Locator | None = None
    chunk_id: str | None = None

    @model_validator(mode='after')
    def location_matches_page(self):
        self.page = checked_page(self.page,self.locator)
        return self


class RetrievalTrace(BaseModel):
    method: str
    query_sha256: str
    chunk_ids: list[str] = Field(default_factory=list)
    context_count: int = 0
    duration_ms: float = 0
    history_turns: int = 0


class RagAnswer(BaseModel):
    """Final grounded answer returned to the caller."""

    question: str
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    chunks: list[RetrievedChunk] = Field(default_factory=list)
    retrieval_trace: RetrievalTrace | None = None


class Summary(BaseModel):
    """Grounded study-oriented summary of a document or subset."""

    scope: Literal["query", "document", "filter", "corpus"]
    target: str | None = None
    summary: str
    key_points: list[str] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)


class MindMap(BaseModel):
    scope: Literal["query", "document", "filter", "corpus"]
    target: str | None = None
    root: MindMapTree
    citations: list[Citation] = Field(default_factory=list)


class QuizItem(BaseModel):
    """A single multiple-choice quiz item grounded in the source material."""

    question: str
    options: list[str] = Field(min_length=4, max_length=4)
    correct_index: int
    explanation: str
    source_markers: list[str] = Field(default_factory=list)
    difficulty: str | None = None
    topic: str | None = None

    @model_validator(mode="after")
    def _validate_correct_index(self) -> "QuizItem":
        if not 0 <= self.correct_index < len(self.options):
            raise ValueError(
                f"correct_index {self.correct_index} out of range for {len(self.options)} options"
            )
        return self


class QuizSet(BaseModel):
    """A reusable set of grounded quiz items with resolved citations."""

    scope: Literal["query", "document", "filter", "corpus"]
    target: str | None = None
    items: list[QuizItem] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)


class Flashcard(BaseModel):
    """A single study flashcard grounded in the source material."""

    front: str
    back: str
    hint: str | None = None
    topic: str | None = None
    source_markers: list[str] = Field(default_factory=list)


class FlashcardSet(BaseModel):
    """A reusable set of grounded flashcards with resolved citations."""

    scope: Literal["query", "document", "filter", "corpus"]
    target: str | None = None
    cards: list[Flashcard] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)

