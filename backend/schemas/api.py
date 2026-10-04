"""Public HTTP contracts, independent of private core chunk metadata."""

from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, field_validator, model_validator


def validate_filename(value: str) -> str:
    value = value.strip()
    if not value or len(value) > 255 or value in {".", ".."}:
        raise ValueError("A non-empty filename of at most 255 characters is required")
    if "/" in value or "\\" in value or any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise ValueError("Use a filename without paths or control characters")
    if not value.lower().endswith(".pdf"):
        raise ValueError("Only PDF filenames are supported")
    return value


Filename = Annotated[str, AfterValidator(validate_filename)]
Page = Annotated[int, Field(strict=True, ge=1)]
Scope = Literal["query", "document", "filter", "corpus"]


class APIModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class HealthResponse(APIModel):
    status: Literal["ok"] = "ok"


class ErrorResponse(APIModel):
    detail: str


class ValidationIssue(APIModel):
    loc: list[str | int]
    msg: str
    type: str


class ValidationErrorResponse(APIModel):
    detail: list[ValidationIssue]


ERROR_RESPONSES = {
    400: {"model": ErrorResponse, "description": "Invalid PDF upload"},
    404: {"model": ErrorResponse, "description": "Selected document or page is not indexed"},
    422: {"model": ValidationErrorResponse, "description": "Request validation failed"},
    500: {"model": ErrorResponse, "description": "Core operation failed; details stay on the server"},
}


class SourceSelection(APIModel):
    filenames: list[Filename] = Field(min_length=1, max_length=64, description="Explicit indexed PDF selection")
    pages: list[Page] = Field(default_factory=list, max_length=1, description="Empty means all pages. One page requires exactly one PDF; multiple pages are unsupported by core.")

    @field_validator("filenames")
    @classmethod
    def unique_names(cls, values: list[str]) -> list[str]:
        return list(dict.fromkeys(values))

    @model_validator(mode="after")
    def supported_page_filter(self):
        if self.pages and len(self.filenames) != 1:
            raise ValueError("A page filter requires exactly one selected PDF")
        return self


class ChatRequest(SourceSelection):
    question: str = Field(min_length=1, max_length=10000, description="Non-empty grounded question")
    k: int = Field(default=6, strict=True, ge=1, le=64)

    @field_validator("question")
    @classmethod
    def non_empty_question(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Question must not be blank")
        return value


class LearningRequest(SourceSelection):
    topic: str | None = Field(default=None, max_length=10000, description="Maps to core query: non-empty topic uses similarity retrieval; otherwise all matching chunks are used.")
    k: int | None = Field(default=None, strict=True, ge=1, le=128, description="Retrieval count only when topic is non-empty; null preserves core default")

    @field_validator("topic")
    @classmethod
    def normalize_topic(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None


class SummaryRequest(LearningRequest):
    pass


class QuizRequest(LearningRequest):
    count: int = Field(default=3, strict=True, ge=1, le=50)


class FlashcardsRequest(LearningRequest):
    count: int = Field(default=3, strict=True, ge=1, le=100)


class DocumentInfo(APIModel):
    filename: Filename
    document_id: str
    pages: list[Page]
    page_count: int = Field(ge=0)
    chunk_count: int = Field(ge=0)


class DocumentsResponse(APIModel):
    documents: list[DocumentInfo]


class UploadResponse(APIModel):
    filename: Filename
    chunks_indexed: int = Field(ge=0)


class Citation(APIModel):
    source_index: int = Field(ge=1)
    source_marker: str = Field(pattern=r"^S[1-9][0-9]*$", description="Marker without brackets, e.g. S1")
    filename: Filename
    page: Page
    source_text: str | None = Field(default=None, description="Source chunk text deliberately included for expandable citations and complete Markdown exports")
    section: str | None = None
    chunk_id: str | None = None


class ChatResponse(APIModel):
    question: str
    answer: str
    citations: list[Citation] = Field(default_factory=list)


class LearningResponse(APIModel):
    scope: Scope
    target: str | None = None
    citations: list[Citation] = Field(default_factory=list)


class SummaryResponse(LearningResponse):
    summary: str
    key_points: list[str] = Field(default_factory=list)


class QuizItem(APIModel):
    question: str
    options: list[str] = Field(min_length=4, max_length=4)
    correct_index: int = Field(strict=True, ge=0, le=3)
    explanation: str
    source_markers: list[str] = Field(default_factory=list)
    difficulty: str | None = None
    topic: str | None = None


class QuizResponse(LearningResponse):
    items: list[QuizItem] = Field(default_factory=list)


class Flashcard(APIModel):
    front: str
    back: str
    hint: str | None = None
    topic: str | None = None
    source_markers: list[str] = Field(default_factory=list)


class FlashcardsResponse(LearningResponse):
    cards: list[Flashcard] = Field(default_factory=list)


class ChatExportRequest(APIModel):
    feature: Literal["chat"]
    result: ChatResponse


class SummaryExportRequest(APIModel):
    feature: Literal["summary"]
    result: SummaryResponse


class QuizExportRequest(APIModel):
    feature: Literal["quiz"]
    result: QuizResponse


class FlashcardsExportRequest(APIModel):
    feature: Literal["flashcards"]
    result: FlashcardsResponse


ExportRequest = Annotated[
    ChatExportRequest | SummaryExportRequest | QuizExportRequest | FlashcardsExportRequest,
    Field(discriminator="feature"),
]
