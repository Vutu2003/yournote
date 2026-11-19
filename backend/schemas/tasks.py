"""Explicit, nonsecret per-task snapshots and backward-compatible result metadata."""
from typing import Annotated, Literal
from pydantic import Field, model_validator

from backend.schemas.api import APIModel, ChatRequest, SourceSelection, SummaryRequest, QuizRequest, FlashcardsRequest, MindMapRequest
from backend.schemas.reading import ReadingChatRequest
from backend.schemas.api import ComparisonRequest,ReportRequest,GraphRequest
from src.providers.contracts import ReasoningEffort


class ModelChoice(APIModel):
    provider: Literal['gemini', 'chatgpt']
    model: str = Field(min_length=1, max_length=255, pattern=r'^[A-Za-z0-9][A-Za-z0-9._:/-]*$')
    connection_id: str | None = Field(default=None, min_length=1, max_length=64)

    reasoning_effort: ReasoningEffort | None = None

    @model_validator(mode='after')
    def validate_connection(self):
        if (self.provider == 'chatgpt') != (self.connection_id is not None):
            raise ValueError('ChatGPT requires a saved connection; server API does not accept one')
        if self.provider != 'chatgpt' and self.reasoning_effort is not None:
            raise ValueError('Server API does not support reasoning effort selection')
        return self


class TaskBase(APIModel):
    id: str = Field(pattern=r'^[a-f0-9-]{36}$')
    notebook_id: str = Field(min_length=1, max_length=64)
    model: ModelChoice


class ChatTask(TaskBase):
    feature: Literal['chat']
    input: ChatRequest


class ReadingTask(TaskBase):
    feature: Literal['reading']
    input: ReadingChatRequest
    sources: SourceSelection


class SummaryTask(TaskBase):
    feature: Literal['summary']
    input: SummaryRequest


class QuizTask(TaskBase):
    feature: Literal['quiz']
    input: QuizRequest


class FlashcardsTask(TaskBase):
    feature: Literal['flashcards']
    input: FlashcardsRequest


class MindMapTask(TaskBase):
    feature: Literal['mindmap']
    input: MindMapRequest


class ComparisonTask(TaskBase):
    feature:Literal['comparison']
    input:ComparisonRequest

class ReportTask(TaskBase):
    feature:Literal['report']
    input:ReportRequest


class GraphTask(TaskBase):
    feature:Literal['graph']
    input:GraphRequest


TaskRequest = Annotated[ChatTask | ReadingTask | SummaryTask | QuizTask | FlashcardsTask | MindMapTask | ComparisonTask | ReportTask | GraphTask,
                        Field(discriminator='feature')]
