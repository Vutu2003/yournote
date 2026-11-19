"""Only completed generation metadata can be persisted in notebook history."""
from typing import Literal
from pydantic import Field
from backend.schemas.api_base import APIModel
from src.providers.contracts import ReasoningEffort


class ReportedUsage(APIModel):
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)


class GenerationMetadata(APIModel):
    provider: Literal['gemini', 'chatgpt']
    reasoning_effort: ReasoningEffort | None = None
    requested_model: str = Field(min_length=1, max_length=255)
    model: str | None = Field(default=None, max_length=255)
    actual_models: list[str] = Field(default_factory=list, max_length=64)
    created_at: str = Field(max_length=64)
    status: Literal['completed'] = 'completed'
    request_id: str = Field(max_length=64)
    notebook_id: str = Field(max_length=64)
    source_versions: dict[str, str] = Field(default_factory=dict, max_length=64)
    source_filenames: list[str] = Field(max_length=64)
    pages: list[int] = Field(default_factory=list, max_length=1)
    calls: int = Field(ge=0, le=64)
    duration_seconds: float = Field(ge=0)
    usage: ReportedUsage | None = None
