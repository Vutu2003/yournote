"""LLM invocation through Gemini API (google-genai)."""

from __future__ import annotations

from contextvars import ContextVar
import logging
import time

import httpx
from google import genai
from google.genai import errors, types

from src.config import settings
from src.errors import LLMServiceError


_runtime_api_key: ContextVar[str | None] = ContextVar("runtime_gemini_api_key", default=None)
_TRANSIENT_CODES = {408, 500, 502, 503, 504}
_MAX_ATTEMPTS = 3
logger = logging.getLogger(__name__)

def set_runtime_gemini_api_key(api_key: str | None) -> None:
    _runtime_api_key.set(api_key.strip() if isinstance(api_key, str) else None)

def invoke_llm(prompt: str) -> str:
    """Invoke the configured chat model and return plain text.

    Args: prompt.
    Returns: assistant text content.
    Raises: RuntimeError if the API key is missing or response is empty.
    """
    api_key = _runtime_api_key.get() or settings.gemini_api_key
    if not api_key:
        raise LLMServiceError(503, "AI service is not configured.")

    # Own one bounded retry loop. Disable nested SDK retries so an overloaded
    # model cannot multiply attempts, and always release HTTP connections.
    with genai.Client(api_key=api_key, http_options=types.HttpOptions(
        timeout=60_000, retry_options=types.HttpRetryOptions(attempts=1),
    )) as client:
        for attempt in range(_MAX_ATTEMPTS):
            try:
                resp = client.models.generate_content(
                    model=settings.llm_model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=settings.llm_temperature,
                        max_output_tokens=settings.llm_max_new_tokens,
                    ),
                )
                break
            except errors.APIError as exc:
                if exc.code == 429:
                    raise LLMServiceError(429, "AI service rate limit exceeded.") from exc
                if exc.code in (401, 403):
                    raise LLMServiceError(502, "AI service authentication failed.") from exc
                if exc.code == 404:
                    raise LLMServiceError(502, "Configured AI model is unavailable.") from exc
                if exc.code not in _TRANSIENT_CODES:
                    raise LLMServiceError(502, "AI service rejected the request.") from exc
                failure = LLMServiceError(503, "AI service is temporarily unavailable.")
                cause = exc
            except httpx.TimeoutException as exc:
                failure = LLMServiceError(504, "AI service timed out.")
                cause = exc
            except httpx.TransportError as exc:
                failure = LLMServiceError(503, "AI service is temporarily unavailable.")
                cause = exc
            if attempt + 1 == _MAX_ATTEMPTS:
                raise failure from cause
            delay = 2 ** attempt
            logger.info("Temporary AI failure; retrying attempt %d/%d in %ds", attempt + 2, _MAX_ATTEMPTS, delay)
            time.sleep(delay)
    text = (resp.text or "").strip()
    if not text:
        raise LLMServiceError(502, "AI service returned an empty response.")
    return text

