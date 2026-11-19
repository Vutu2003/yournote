"""Gemini SDK details, bounded retries and safe failure translation."""

from __future__ import annotations

import logging
import time

from google import genai
from google.genai import errors, types
import httpx
from pydantic import SecretStr

from src.errors import LLMErrorCode, LLMServiceError
from src.providers.contracts import (
    CancellationToken, ExecutionContext, LLMRequest, LLMResult,
    ProviderCapabilities, TokenUsage, TextDelta, Completion,
)

logger = logging.getLogger(__name__)
_TRANSIENT_CODES = {408, 500, 502, 503, 504}
_MAX_ATTEMPTS = 3


def _usage(response) -> TokenUsage | None:
    metadata = getattr(response, "usage_metadata", None)
    if metadata is None:
        return None

    def count(name: str) -> int | None:
        value = getattr(metadata, name, None)
        return value if type(value) is int and value >= 0 else None

    values = TokenUsage(
        input_tokens=count("prompt_token_count"),
        output_tokens=count("candidates_token_count"),
        total_tokens=count("total_token_count"),
    )
    return values if any(value is not None for value in (
        values.input_tokens, values.output_tokens, values.total_tokens,
    )) else None


class GeminiProvider:
    # Advertise only features implemented here. JSON prompts are not schema mode.
    capabilities = ProviderCapabilities(
        streaming=True,
        supported_parameters=frozenset({"temperature", "max_output_tokens"}),
    )

    def generate(
        self, request: LLMRequest, context: ExecutionContext, *,
        credential: SecretStr, cancellation: CancellationToken,
    ) -> LLMResult:
        self.capabilities.validate(request)
        cancellation.raise_if_cancelled()
        started = time.monotonic()
        config = {}
        if request.parameters.temperature is not None:
            config["temperature"] = request.parameters.temperature
        if request.parameters.max_output_tokens is not None:
            config["max_output_tokens"] = request.parameters.max_output_tokens
        try:
            # Disable SDK retries: one bounded loop owns the total attempts.
            with genai.Client(api_key=credential.get_secret_value(), http_options=types.HttpOptions(
                timeout=60_000, retry_options=types.HttpRetryOptions(attempts=1),
            )) as client:
                remove_close = cancellation.on_cancel(client.close)
                for attempt in range(_MAX_ATTEMPTS):
                    cancellation.raise_if_cancelled()
                    try:
                        response = client.models.generate_content(
                            model=context.selection.model,
                            contents=request.prompt,
                            config=types.GenerateContentConfig(**config),
                        )
                        break
                    except errors.APIError as exc:
                        if exc.code == 429:
                            # A bare 429 doesn't establish exhausted plan quota.
                            raise LLMServiceError.for_code(LLMErrorCode.RATE_LIMITED) from None
                        if exc.code in (401, 403):
                            raise LLMServiceError.for_code(LLMErrorCode.RECONNECT_REQUIRED) from None
                        if exc.code == 404:
                            raise LLMServiceError.for_code(LLMErrorCode.MODEL_UNAVAILABLE) from None
                        if exc.code not in _TRANSIENT_CODES:
                            raise LLMServiceError.for_code(LLMErrorCode.REQUEST_REJECTED) from None
                        failure = LLMErrorCode.TEMPORARILY_UNAVAILABLE
                    except httpx.TimeoutException:
                        failure = LLMErrorCode.TIMEOUT
                    except httpx.TransportError:
                        failure = LLMErrorCode.TEMPORARILY_UNAVAILABLE
                    if attempt + 1 == _MAX_ATTEMPTS:
                        raise LLMServiceError.for_code(failure) from None
                    logger.info("Temporary AI failure; retrying attempt %d/%d", attempt + 2, _MAX_ATTEMPTS)
                    cancellation.wait(2 ** attempt)
                    cancellation.raise_if_cancelled()
            cancellation.raise_if_cancelled()
            text = response.text
            candidates = getattr(response, 'candidates', None) or []
            if any(getattr(candidate, 'finish_reason', None) and str(candidate.finish_reason).split('.')[-1] != 'STOP' for candidate in candidates):
                raise LLMServiceError.for_code(LLMErrorCode.INVALID_RESPONSE)
            if not isinstance(text, str) or not text.strip():
                raise LLMServiceError.for_code(LLMErrorCode.INVALID_RESPONSE)
            actual_model = getattr(response, "model_version", None)
            return LLMResult(
                text=text.strip(), provider="gemini",
                model=actual_model if isinstance(actual_model, str) and actual_model.strip() else None,
                duration_seconds=time.monotonic() - started, usage=_usage(response),
            )
        except LLMServiceError:
            raise
        except Exception:
            # Constructor/decoding/shutdown failures can contain credentials.
            raise LLMServiceError.for_code(LLMErrorCode.REQUEST_REJECTED) from None
        finally:
            if 'remove_close' in locals():
                remove_close()

    def stream(self, request: LLMRequest, context: ExecutionContext, *,
               credential: SecretStr, cancellation: CancellationToken):
        self.capabilities.validate(request)
        cancellation.raise_if_cancelled()
        started = time.monotonic()
        config = {}
        if request.parameters.temperature is not None:
            config['temperature'] = request.parameters.temperature
        if request.parameters.max_output_tokens is not None:
            config['max_output_tokens'] = request.parameters.max_output_tokens
        try:
            with genai.Client(api_key=credential.get_secret_value(), http_options=types.HttpOptions(
                timeout=60_000, retry_options=types.HttpRetryOptions(attempts=1),
            )) as client:
                remove_close = cancellation.on_cancel(client.close)
                stream = client.models.generate_content_stream(model=context.selection.model, contents=request.prompt,
                                                               config=types.GenerateContentConfig(**config))
                text, model, usage, finish = [], None, None, None
                try:
                    for chunk in stream:
                        cancellation.raise_if_cancelled()
                        if isinstance(chunk.text, str) and chunk.text:
                            text.append(chunk.text)
                            yield TextDelta(chunk.text)
                        model = getattr(chunk, 'model_version', None) or model
                        usage = _usage(chunk) or usage
                        candidates = getattr(chunk, 'candidates', None) or []
                        for candidate in candidates:
                            finish = getattr(candidate, 'finish_reason', None) or finish
                finally:
                    stream.close()
                cancellation.raise_if_cancelled()
                if str(finish).split('.')[-1] != 'STOP' or not ''.join(text).strip():
                    raise LLMServiceError.for_code(LLMErrorCode.INVALID_RESPONSE)
                yield Completion(LLMResult(text=''.join(text).strip(), provider='gemini', model=model,
                                           usage=usage, duration_seconds=time.monotonic() - started))
        except LLMServiceError:
            raise
        except errors.APIError as exc:
            code = {429: LLMErrorCode.RATE_LIMITED, 401: LLMErrorCode.RECONNECT_REQUIRED,
                    403: LLMErrorCode.RECONNECT_REQUIRED, 404: LLMErrorCode.MODEL_UNAVAILABLE}.get(
                        exc.code, LLMErrorCode.TEMPORARILY_UNAVAILABLE if exc.code in _TRANSIENT_CODES else LLMErrorCode.REQUEST_REJECTED)
            raise LLMServiceError.for_code(code) from None
        except httpx.TimeoutException:
            raise LLMServiceError.for_code(LLMErrorCode.TIMEOUT) from None
        except Exception:
            raise LLMServiceError.for_code(LLMErrorCode.TEMPORARILY_UNAVAILABLE) from None
        finally:
            if 'remove_close' in locals():
                remove_close()
