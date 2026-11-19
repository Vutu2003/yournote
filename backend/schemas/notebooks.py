"""Durable notebook metadata and workspace state."""

from typing import Annotated, Generic, Literal, TypeVar

from pydantic import Field, field_validator, model_validator

from backend.schemas.api import APIModel, ChatResponse, Filename, FlashcardsResponse, QuizResponse, SummaryResponse, MindMapResponse, ComparisonResponse, ReportResponse, GraphResponse

Result = TypeVar("Result")


class NotebookReset(APIModel):
    confirmation: Literal["ĐẶT LẠI"]


class StudioArtifact(APIModel, Generic[Result]):
    id: str
    title: str
    createdAt: int = Field(ge=0)
    sourceFilenames: list[Filename]
    pages: list[int]
    topic: str | None
    result: Result


    @model_validator(mode="after")
    def research_snapshot_matches(self):
        if isinstance(self.result,(ComparisonResponse,ReportResponse,GraphResponse)):
            names=[source.filename for source in self.result.sources]
            if names!=self.sourceFilenames:
                raise ValueError('Research artifact sources disagree with its snapshot')
            metadata=self.result.generation
            if metadata and (metadata.source_filenames!=names or metadata.source_versions!={source.filename:source.document_version for source in self.result.sources}):
                raise ValueError('Research generation metadata disagrees with source versions')
        return self


class UserNote(APIModel):
    id: str = Field(min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")
    title: str = Field(default="Ghi chú chưa đặt tên", min_length=1, max_length=160)
    content: str = Field(default="", max_length=100000)
    createdAt: int = Field(ge=0)
    updatedAt: int = Field(ge=0)

    @field_validator("title")
    @classmethod
    def normalize_title(cls, title: str):
        if not title.strip():
            raise ValueError("Note title must not be blank")
        return title.strip()

    @model_validator(mode="after")
    def valid_timestamps(self):
        if self.updatedAt < self.createdAt:
            raise ValueError("Note update time must not precede creation")
        return self


class WorkspaceState(APIModel):
    schema_version: Literal[1, 2, 3] = 3
    document_filenames: list[Filename] = Field(default_factory=list, max_length=64)
    source_names: dict[Filename, Annotated[str, Field(min_length=1, max_length=160)]] = Field(default_factory=dict, max_length=64)
    selected: list[Filename] = Field(default_factory=list, max_length=64)
    read_documents: list[Filename] = Field(default_factory=list, max_length=64)
    page: str = Field(default="", max_length=10, pattern=r"^(?:[1-9][0-9]*)?$")
    active_tool: Literal["summary", "quiz", "flashcards", "mindmap", "notes", "comparison", "report", "graph"] = "summary"
    notes: list[UserNote] = Field(default_factory=list, max_length=100)
    chat: list[ChatResponse] = Field(default_factory=list)
    summary_artifacts: list[StudioArtifact[SummaryResponse]] = Field(default_factory=list)
    quiz_artifacts: list[StudioArtifact[QuizResponse]] = Field(default_factory=list)
    flashcard_artifacts: list[StudioArtifact[FlashcardsResponse]] = Field(default_factory=list)
    mindmap_artifacts: list[StudioArtifact[MindMapResponse]] = Field(default_factory=list)

    comparison_artifacts: list[StudioArtifact[ComparisonResponse]] = Field(default_factory=list)
    report_artifacts: list[StudioArtifact[ReportResponse]] = Field(default_factory=list)
    graph_artifacts: list[StudioArtifact[GraphResponse]] = Field(default_factory=list)

    @field_validator("source_names")
    @classmethod
    def validate_source_names(cls, names: dict[str, str]):
        normalized = {}
        for filename, name in names.items():
            title = name.strip()
            if not title or any(ord(char) < 32 or ord(char) == 127 for char in title):
                raise ValueError("Source name must be non-empty, single-line text")
            normalized[filename] = title
        return normalized

    @model_validator(mode="after")
    def normalize_selection(self):
        self.document_filenames = list(dict.fromkeys(self.document_filenames))
        self.source_names = {filename: name for filename, name in self.source_names.items() if filename in self.document_filenames and name != filename}
        self.selected = list(dict.fromkeys(name for name in self.selected if name in self.document_filenames))
        self.read_documents = list(dict.fromkeys(name for name in self.read_documents if name in self.document_filenames))
        if len({note.id for note in self.notes}) != len(self.notes):
            raise ValueError("Note identifiers must be unique within a notebook")
        if len(self.selected) != 1 or not self.selected[0].lower().endswith(".pdf"):
            self.page = ""
        return self


class NotebookCreate(APIModel):
    title: str = Field(default="Sổ ghi chú chưa đặt tên", min_length=1, max_length=160)
    icon: str = Field(default="📓", min_length=1, max_length=16)

    @field_validator("title")
    @classmethod
    def non_empty_title(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Title must not be blank")
        return value.strip()


class NotebookUpdate(NotebookCreate):
    state: WorkspaceState


class NotebookInfo(NotebookCreate):
    id: str
    created_at: str
    updated_at: str
    source_count: int
    chat_count: int


class Notebook(NotebookInfo):
    state: WorkspaceState


class NotebooksResponse(APIModel):
    notebooks: list[NotebookInfo]
