"""Public HTTP contracts, independent of private core chunk metadata."""

from typing import Annotated, Literal

from pydantic import AfterValidator, Field, field_validator, model_validator
from src.schemas import MindMapTree, RetrievalTrace
from src.locations import Locator, checked_page
from backend.schemas.api_base import APIModel
from backend.schemas.generation import GenerationMetadata


def validate_filename(value: str) -> str:
    value = value.strip()
    if not value or len(value) > 255 or value in {".", ".."}:
        raise ValueError("A non-empty filename of at most 255 characters is required")
    if "/" in value or "\\" in value or any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise ValueError("Use a filename without paths or control characters")
    if not value.lower().endswith((".pdf", ".docx", ".md", ".txt")):
        raise ValueError("Supported filenames: PDF, DOCX, Markdown and TXT")
    return value


Filename = Annotated[str, AfterValidator(validate_filename)]
Page = Annotated[int, Field(strict=True, ge=1)]
Scope = Literal["query", "document", "filter", "corpus"]


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
    429: {"model": ErrorResponse, "description": "AI service rate limit or quota exceeded"},
    500: {"model": ErrorResponse, "description": "Core operation failed; details stay on the server"},
    502: {"model": ErrorResponse, "description": "AI service rejected the request"},
    503: {"model": ErrorResponse, "description": "AI service temporarily unavailable"},
    504: {"model": ErrorResponse, "description": "AI service timed out"},
}


class SourceSelection(APIModel):
    document_versions: dict[Filename, Annotated[str, Field(pattern=r'^[a-f0-9]{64}$')]] = Field(default_factory=dict, max_length=64)
    filenames: list[Filename] = Field(min_length=1, max_length=64, description="Explicit indexed document selection")
    pages: list[Page] = Field(default_factory=list, max_length=1, description="Empty means all pages. One page requires exactly one PDF; multiple pages are unsupported by core.")

    @field_validator("filenames")
    @classmethod
    def unique_names(cls, values: list[str]) -> list[str]:
        return list(dict.fromkeys(values))

    @model_validator(mode="after")
    def supported_page_filter(self):
        if not set(self.document_versions) <= set(self.filenames):
            raise ValueError('Version snapshots must belong to selected sources')
        if self.pages and not self.filenames[0].lower().endswith('.pdf'):
            raise ValueError('Page filters are only supported for PDF')
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


class MindMapRequest(LearningRequest):
    pass


class QuizRequest(LearningRequest):
    count: int = Field(default=3, strict=True, ge=1, le=50)


class FlashcardsRequest(LearningRequest):
    count: int = Field(default=3, strict=True, ge=1, le=100)


class DocumentInfo(APIModel):
    schema_version: int = Field(default=1, exclude_if=lambda value: value == 1)
    original_filename: str | None = Field(default=None, exclude_if=lambda value: value is None)
    kind: Literal['pdf', 'docx', 'markdown', 'text'] = Field(default='pdf', exclude_if=lambda value: value == 'pdf')
    document_version: str | None = Field(default=None, pattern=r'^[a-f0-9]{64}$', exclude_if=lambda value: value is None)
    anchor_count: int = Field(default=0, ge=0, exclude_if=lambda value: value == 0)
    warnings: list[str] = Field(default_factory=list, exclude_if=lambda value: not value)
    filename: Filename
    document_id: str
    pages: list[Page]
    page_count: int = Field(ge=0)
    chunk_count: int = Field(ge=0)


class DocumentsResponse(APIModel):
    documents: list[DocumentInfo]


class UploadResponse(APIModel):
    document_id: str | None = Field(default=None, exclude_if=lambda value: value is None)
    document_version: str | None = Field(default=None, exclude_if=lambda value: value is None)
    original_filename: str | None = Field(default=None, exclude_if=lambda value: value is None)
    deduplicated: bool = Field(default=False, exclude_if=lambda value: not value)
    warnings: list[str] = Field(default_factory=list, exclude_if=lambda value: not value)
    filename: Filename
    chunks_indexed: int = Field(ge=0)


class Citation(APIModel):
    schema_version: int = Field(default=1, exclude_if=lambda value: value == 1)
    document_id: str | None = Field(default=None, exclude_if=lambda value: value is None)
    document_version: str | None = Field(default=None, pattern=r'^[a-f0-9]{64}$', exclude_if=lambda value: value is None)
    locator: Locator | None = Field(default=None, exclude_if=lambda value: value is None)
    source_index: int = Field(ge=1)
    source_marker: str = Field(pattern=r"^S[1-9][0-9]*$", description="Marker without brackets, e.g. S1")
    filename: Filename
    page: Page | None = None
    source_text: str | None = Field(default=None, description="Source chunk text deliberately included for expandable citations and complete Markdown exports")
    section: str | None = None
    chunk_id: str | None = None

    @model_validator(mode='after')
    def location_matches_page(self):
        self.page = checked_page(self.page,self.locator)
        return self


class SelectedPassage(APIModel):
    filename: Filename
    document_id: str = Field(min_length=1, max_length=128)
    document_version: str = Field(pattern=r"^[a-f0-9]{64}$")
    page: Page
    text: str = Field(min_length=1, max_length=10000)


class ChatContext(APIModel):
    mode: Literal["reading"] = "reading"
    scope: Literal["document", "notebook"]
    filenames: list[Filename]
    selection: SelectedPassage | None = None


class ChatResponse(APIModel):
    retrieval_trace: RetrievalTrace | None = Field(default=None, exclude_if=lambda value: value is None)
    question: str
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    context: ChatContext | None = None
    generation: GenerationMetadata | None = Field(default=None, exclude_if=lambda value: value is None)


class LearningResponse(APIModel):
    scope: Scope
    target: str | None = None
    citations: list[Citation] = Field(default_factory=list)
    generation: GenerationMetadata | None = Field(default=None, exclude_if=lambda value: value is None)


class SummaryResponse(LearningResponse):
    summary: str
    key_points: list[str] = Field(default_factory=list)


class MindMapResponse(LearningResponse):
    root: MindMapTree


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


from src.research_schemas import Comparison, StudyReport, KnowledgeGraph

class ResearchRequest(SourceSelection):
    goal: str = Field(min_length=1,max_length=2000)
    @field_validator('goal')
    @classmethod
    def required_goal(cls,value):
        if not value.strip(): raise ValueError('A learning goal is required')
        return value.strip()
    @model_validator(mode='after')
    def research_bounds(self):
        if len(self.filenames)>6: raise ValueError('Research tools support at most 6 selected sources')
        return self

class ComparisonRequest(ResearchRequest):
    criteria: list[Annotated[str,Field(min_length=1,max_length=160)]] = Field(min_length=1,max_length=6)
    @field_validator('criteria')
    @classmethod
    def unique_criteria(cls,values):
        values=[v.strip() for v in values]
        if any(not v for v in values) or len({v.casefold() for v in values})!=len(values): raise ValueError('Criteria must be non-empty and unique')
        return values
    @model_validator(mode='after')
    def multiple_sources(self):
        if len(self.filenames)<2: raise ValueError('Comparison requires at least 2 selected sources')
        return self

class ReportRequest(ResearchRequest):
    mode: Literal['study_guide','explanation','synthesis']='study_guide'

class GraphRequest(ResearchRequest):
    pass

class GraphResponse(KnowledgeGraph):
    generation: GenerationMetadata | None = Field(default=None,exclude_if=lambda value:value is None)

class GraphExportRequest(APIModel):
    feature:Literal['graph']
    result:GraphResponse

class ComparisonResponse(Comparison):
    generation: GenerationMetadata | None = Field(default=None,exclude_if=lambda value:value is None)

class ReportResponse(StudyReport):
    generation: GenerationMetadata | None = Field(default=None,exclude_if=lambda value:value is None)

class ComparisonExportRequest(APIModel):
    feature:Literal['comparison']
    result:ComparisonResponse

class ReportExportRequest(APIModel):
    feature:Literal['report']
    result:ReportResponse


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


class MindMapExportRequest(APIModel):
    feature: Literal["mindmap"]
    result: MindMapResponse


ExportRequest = Annotated[
    ChatExportRequest | SummaryExportRequest | QuizExportRequest | FlashcardsExportRequest | MindMapExportRequest | ComparisonExportRequest | ReportExportRequest | GraphExportRequest,
    Field(discriminator="feature"),
]
