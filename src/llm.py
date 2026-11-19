"""Provider dispatch and scoped execution; the legacy invoke_llm returns text."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from functools import wraps
from threading import Lock
from typing import ParamSpec, TypeVar

from pydantic import SecretStr

from src.config import settings
from src.errors import LLMErrorCode, LLMServiceError
from src.providers.contracts import (
    CancellationToken, CredentialRef, CredentialResolver, ExecutionContext,
    Completion, GenerationParameters, LLMProvider, LLMRequest, LLMResult, ModelSelection, TextDelta,
)


class CallBudget:
    def __init__(self, limit: int | None):
        self.limit, self.used = limit, 0
        self.lock = Lock()

    def reserve(self):
        with self.lock:
            self.check(1)
            self.used += 1

    def check(self, count):
        if self.limit is not None and self.used + count > self.limit:
            raise LLMServiceError(422, "Selected material exceeds the AI task call limit.", code=LLMErrorCode.INVALID_REQUEST)


@dataclass(frozen=True, slots=True)
class _TaskState:
    context: ExecutionContext
    resolver: CredentialResolver = field(repr=False)
    cancellation: CancellationToken = field(repr=False)
    budget: CallBudget = field(repr=False)
    on_delta: Callable[[str], None] | None = field(default=None, repr=False)
    on_result: Callable[[LLMResult], None] | None = field(default=None, repr=False)


_task_state: ContextVar[_TaskState | None] = ContextVar("llm_task", default=None)
_ENVIRONMENT_CREDENTIAL = CredentialRef()
_P = ParamSpec("_P")
_T = TypeVar("_T")


def default_context() -> ExecutionContext:
    """Snapshot model and generation settings once per whole operation."""
    return ExecutionContext(
        selection=ModelSelection(provider=settings.llm_provider, model=settings.llm_model),
        parameters=GenerationParameters(
            temperature=settings.llm_temperature,
            max_output_tokens=settings.llm_max_new_tokens,
        ),
    )


def current_context() -> ExecutionContext | None:
    state = _task_state.get()
    return state.context if state else None


def check_workload(calls: int) -> None:
    state = _task_state.get()
    if state:
        state.cancellation.raise_if_cancelled()
        state.budget.check(calls)


def get_provider(name: str) -> LLMProvider:
    """Explicit backend-only dispatch. No SDK imports during health/OpenAPI."""
    if name == "gemini":
        from src.providers.gemini import GeminiProvider

        return GeminiProvider()
    if name == "chatgpt":
        from src.providers.chatgpt import ChatGPTProvider

        return ChatGPTProvider()
    raise LLMServiceError.for_code(LLMErrorCode.UNSUPPORTED_PROVIDER)


def _environment_resolver() -> CredentialResolver:
    # Capture once, so map/reduce cannot switch credentials partway through.
    raw = settings.gemini_api_key
    secret = SecretStr(raw) if raw else None

    def resolve(reference: CredentialRef) -> SecretStr | None:
        return secret if reference == _ENVIRONMENT_CREDENTIAL else None

    return resolve


@contextmanager
def llm_task(
    context: ExecutionContext | None = None, *,
    credential_resolver: CredentialResolver | None = None,
    cancellation: CancellationToken | None = None,
    on_delta: Callable[[str], None] | None = None,
    on_result: Callable[[LLMResult], None] | None = None,
    max_calls: int | None = None,
) -> Iterator[ExecutionContext]:
    """Scope a whole operation; nested calls inherit when no override is given.

    Backends may install a verified connection/model context here, before calling
    existing services. Never resolve untrusted HTTP credentials. Every installed
    ContextVar token is reset, including after errors and cancellation.
    """
    active = _task_state.get()
    if (active is not None and context is None and credential_resolver is None and cancellation is None
            and on_delta is None and on_result is None and max_calls is None):
        yield active.context
        return
    selected = context if context is not None else (active.context if active else default_context())
    get_provider(selected.selection.provider)  # Fail even when retrieval finds no chunks.
    inherited = active if context is None else None
    if credential_resolver is not None:
        resolver = credential_resolver
    elif inherited is not None:
        resolver = inherited.resolver
    elif selected.selection.provider == "gemini":
        resolver = _environment_resolver()
    else:
        resolver = lambda reference: None
    cancel = cancellation if cancellation is not None else (
        inherited.cancellation if inherited else CancellationToken()
    )
    state = _TaskState(selected, resolver, cancel,
                       inherited.budget if inherited and max_calls is None else CallBudget(max_calls),
                       on_delta if on_delta is not None else (inherited.on_delta if inherited else None),
                       on_result if on_result is not None else (inherited.on_result if inherited else None))
    token = _task_state.set(state)
    try:
        yield selected
    finally:
        _task_state.reset(token)


def llm_operation(function: Callable[_P, _T]) -> Callable[_P, _T]:
    """Group retrieval and every map/reduce call under one execution snapshot."""
    @wraps(function)
    def scoped(*args: _P.args, **kwargs: _P.kwargs) -> _T:
        with llm_task():
            return function(*args, **kwargs)

    return scoped


def generate_llm(request: LLMRequest) -> LLMResult:
    """Internal result API. Public RAG and notebook schemas stay unchanged."""
    with llm_task():
        state = _task_state.get()
        assert state is not None
        state.cancellation.raise_if_cancelled()
        provider = get_provider(state.context.selection.provider)
        provider.capabilities.validate(request)
        try:
            credential = state.resolver(state.context.credential_ref)
        except LLMServiceError:
            raise
        except Exception:
            raise LLMServiceError.for_code(LLMErrorCode.RECONNECT_REQUIRED) from None
        if credential is None or not isinstance(credential, SecretStr) or not credential.get_secret_value():
            code = (LLMErrorCode.NOT_CONFIGURED if state.context.credential_ref == _ENVIRONMENT_CREDENTIAL
                    else LLMErrorCode.RECONNECT_REQUIRED)
            raise LLMServiceError.for_code(code)
        state.budget.reserve()
        try:
            if state.on_delta is not None:
                if not provider.capabilities.streaming:
                    raise LLMServiceError.for_code(LLMErrorCode.UNSUPPORTED_CAPABILITY)
                stream = provider.stream(request, state.context, credential=credential, cancellation=state.cancellation)
                result = None
                try:
                    for event in stream:
                        state.cancellation.raise_if_cancelled()
                        if isinstance(event, TextDelta):
                            state.on_delta(event.text)
                        elif isinstance(event, Completion):
                            result = event.result
                            break
                        else:
                            raise LLMServiceError.for_code(LLMErrorCode.INVALID_RESPONSE)
                finally:
                    stream.close()
            else:
                result = provider.generate(
                    request, state.context, credential=credential, cancellation=state.cancellation,
                )
        except LLMServiceError:
            state.cancellation.raise_if_cancelled()
            raise
        except Exception:
            state.cancellation.raise_if_cancelled()
            raise LLMServiceError.for_code(LLMErrorCode.REQUEST_REJECTED) from None
        state.cancellation.raise_if_cancelled()
        if not isinstance(result, LLMResult) or not isinstance(result.text, str) or not result.text.strip():
            raise LLMServiceError.for_code(LLMErrorCode.INVALID_RESPONSE)
        if state.on_result:
            state.on_result(result)
        return result


def invoke_llm(prompt: str) -> str:
    """Compatibility bridge for Chat, reading and all existing Studio prompts."""
    with llm_task() as context:
        return generate_llm(LLMRequest(prompt=prompt, parameters=context.parameters)).text


@contextmanager
def gemini_api_key_scope(api_key: str | None) -> Iterator[ExecutionContext]:
    """Legacy Gradio override with cleanup; blank keeps env behavior."""
    context = default_context()
    if context.selection.provider != "gemini":
        raise LLMServiceError.for_code(LLMErrorCode.UNSUPPORTED_PROVIDER)
    raw = api_key.strip() if isinstance(api_key, str) else ""
    resolver = _environment_resolver()
    if raw:
        secret = SecretStr(raw)

        def resolver(reference: CredentialRef) -> SecretStr | None:
            return secret if reference == _ENVIRONMENT_CREDENTIAL else None

    with llm_task(context, credential_resolver=resolver) as selected:
        yield selected
