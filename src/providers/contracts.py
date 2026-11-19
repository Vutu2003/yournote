"""Small internal contracts; credentials never belong in requests or results."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
import math
import re
from threading import Event, Lock, Thread
from typing import Literal, Protocol
from uuid import uuid4

from pydantic import SecretStr

from src.errors import LLMErrorCode, LLMServiceError


@dataclass(frozen=True, slots=True)
class ModelSelection:
    provider: str
    model: str

    def __post_init__(self) -> None:
        if not isinstance(self.provider, str) or not re.fullmatch(r"[a-z][a-z0-9_-]{0,63}", self.provider):
            raise LLMServiceError.for_code(LLMErrorCode.UNSUPPORTED_PROVIDER)
        if not isinstance(self.model, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,254}", self.model):
            raise LLMServiceError.for_code(LLMErrorCode.MODEL_UNAVAILABLE)


@dataclass(frozen=True, slots=True)
class CredentialRef:
    """Opaque backend connection ID, never an API key or OAuth token."""

    id: str = "environment:gemini"


ReasoningEffort = Literal['none', 'minimal', 'low', 'medium', 'high', 'xhigh', 'max']
REASONING_EFFORTS = ('none', 'minimal', 'low', 'medium', 'high', 'xhigh', 'max')


@dataclass(frozen=True, slots=True)
class GenerationParameters:
    temperature: float | None = None
    max_output_tokens: int | None = None
    reasoning_effort: ReasoningEffort | None = None

    def __post_init__(self) -> None:
        if self.reasoning_effort is not None and self.reasoning_effort not in REASONING_EFFORTS:
            raise LLMServiceError.for_code(LLMErrorCode.INVALID_REQUEST)
        if self.temperature is not None and (
            isinstance(self.temperature, bool) or not isinstance(self.temperature, (int, float))
            or not math.isfinite(self.temperature) or not 0 <= self.temperature <= 2
        ):
            raise LLMServiceError.for_code(LLMErrorCode.INVALID_REQUEST)
        if self.max_output_tokens is not None and (
            type(self.max_output_tokens) is not int or self.max_output_tokens < 1
        ):
            raise LLMServiceError.for_code(LLMErrorCode.INVALID_REQUEST)


@dataclass(frozen=True, slots=True)
class ExecutionContext:
    selection: ModelSelection
    credential_ref: CredentialRef = field(default_factory=CredentialRef)
    request_id: str = field(default_factory=lambda: uuid4().hex)
    parameters: GenerationParameters = field(default_factory=GenerationParameters)


@dataclass(frozen=True, slots=True)
class LLMRequest:
    prompt: str = field(repr=False)
    parameters: GenerationParameters = field(default_factory=GenerationParameters)

    def __post_init__(self) -> None:
        if not isinstance(self.prompt, str) or not self.prompt.strip():
            raise LLMServiceError.for_code(LLMErrorCode.INVALID_REQUEST)


@dataclass(frozen=True, slots=True)
class TokenUsage:
    """Only counts actually reported by the provider. Unknown counts stay None."""

    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None


@dataclass(frozen=True, slots=True)
class LLMResult:
    text: str = field(repr=False)
    provider: str
    model: str | None = None  # Actual model/version, not an invented resolution of an alias.
    duration_seconds: float | None = None
    usage: TokenUsage | None = None


@dataclass(frozen=True, slots=True)
class ProviderCapabilities:
    streaming: bool = False
    structured_output: bool = False  # Native enforcement, not JSON requested in a prompt.
    input_types: frozenset[str] = frozenset({"text"})
    supported_parameters: frozenset[str] = frozenset()

    def validate(self, request: LLMRequest) -> None:
        if "text" not in self.input_types:
            raise LLMServiceError.for_code(LLMErrorCode.UNSUPPORTED_CAPABILITY)
        for name in ("temperature", "max_output_tokens", "reasoning_effort"):
            if getattr(request.parameters, name) is not None and name not in self.supported_parameters:
                raise LLMServiceError.for_code(LLMErrorCode.UNSUPPORTED_CAPABILITY)


class CredentialResolver(Protocol):
    def __call__(self, reference: CredentialRef) -> SecretStr | None: ...


class CancellationToken:
    """Cooperative cancellation. A blocking SDK request cannot yet be interrupted."""

    def __init__(self) -> None:
        self._event = Event()
        self._lock = Lock()
        self._callbacks = []

    def cancel(self) -> None:
        with self._lock:
            if self._event.is_set():
                return
            self._event.set()
            callbacks, self._callbacks = self._callbacks, []
        for callback in callbacks:
            self._close_async(callback)

    @staticmethod
    def _close_async(callback) -> None:
        def close():
            try:
                callback()
            except Exception:
                pass
        Thread(target=close, daemon=True).start()

    def on_cancel(self, callback):
        """Register best-effort transport close, without blocking the cancel request."""
        with self._lock:
            cancelled = self._event.is_set()
            if not cancelled:
                self._callbacks.append(callback)
        if cancelled:
            self._close_async(callback)
        def remove():
            with self._lock:
                if callback in self._callbacks:
                    self._callbacks.remove(callback)
        return remove

    def wait(self, timeout: float) -> bool:
        return self._event.wait(timeout)

    @property
    def cancelled(self) -> bool:
        return self._event.is_set()

    def raise_if_cancelled(self) -> None:
        if self._event.is_set():
            raise LLMServiceError.for_code(LLMErrorCode.CANCELLED)


class LLMProvider(Protocol):
    capabilities: ProviderCapabilities

    def generate(
        self, request: LLMRequest, context: ExecutionContext, *,
        credential: SecretStr, cancellation: CancellationToken,
    ) -> LLMResult: ...


@dataclass(frozen=True, slots=True)
class TextDelta:
    text: str = field(repr=False)
    kind: Literal["delta"] = field(default="delta", init=False)


@dataclass(frozen=True, slots=True)
class Completion:
    result: LLMResult
    kind: Literal["completed"] = field(default="completed", init=False)


class StreamingProvider(LLMProvider, Protocol):
    """Phase 03 contract: delta* then one completion; error/cancel raises, no completion.

    Callers must not persist deltas as successful output. Exhaustion alone does
    not mean completion. Closing the iterator must close the upstream response.
    """

    def stream(
        self, request: LLMRequest, context: ExecutionContext, *,
        credential: SecretStr, cancellation: CancellationToken,
    ) -> Iterator[TextDelta | Completion]: ...
