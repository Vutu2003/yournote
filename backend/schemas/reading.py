"""Original-document reading, normalized highlight rectangles, and scoped chat."""

from typing import Literal

from pydantic import Field, field_validator, model_validator

from backend.schemas.api import APIModel, Filename, Page, SelectedPassage


class ReadingDocument(APIModel):
    document_id: str
    filename: Filename
    document_version: str
    page_count: int


class HighlightRect(APIModel):
    x: float = Field(ge=0, le=1, allow_inf_nan=False)
    y: float = Field(ge=0, le=1, allow_inf_nan=False)
    width: float = Field(gt=0, le=1, allow_inf_nan=False)
    height: float = Field(gt=0, le=1, allow_inf_nan=False)

    @model_validator(mode="after")
    def inside_page(self):
        if self.x + self.width > 1.00001 or self.y + self.height > 1.00001:
            raise ValueError("Highlight rectangles must stay inside the page")
        return self


class HighlightCreate(APIModel):
    document_version: str = Field(pattern=r"^[a-f0-9]{64}$")
    page: Page
    text: str = Field(min_length=1, max_length=10000)
    rects: list[HighlightRect] = Field(min_length=1, max_length=300)
    color: Literal["yellow"] = "yellow"

    @field_validator("text")
    @classmethod
    def text_not_blank(cls, value: str):
        if not value.strip():
            raise ValueError("Highlight text must not be blank")
        return value.strip()


class Highlight(HighlightCreate):
    id: str
    document_id: str
    created_at: str


class HighlightsResponse(APIModel):
    highlights: list[Highlight]


class ReadingChatRequest(APIModel):
    document_id: str = Field(min_length=1, max_length=128)
    scope: Literal["document", "notebook"] = "document"
    question: str = Field(min_length=1, max_length=10000)
    k: int = Field(default=6, strict=True, ge=1, le=64)
    selection: SelectedPassage | None = None

    @field_validator("question")
    @classmethod
    def question_not_blank(cls, value: str):
        if not value.strip():
            raise ValueError("Question must not be blank")
        return value.strip()

    @model_validator(mode="after")
    def selection_scope(self):
        if self.selection and self.scope != "document":
            raise ValueError("A selected passage requires document scope")
        return self
