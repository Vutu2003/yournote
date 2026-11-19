"""Official ChatGPT plan-usage Responses route; no API-key billing fallback."""
from __future__ import annotations

import json
import time
from contextlib import contextmanager

import httpx
from pydantic import SecretStr

from src.errors import LLMErrorCode, LLMServiceError
from src.providers.contracts import CancellationToken, ExecutionContext, LLMRequest, LLMResult, ProviderCapabilities, TokenUsage, TextDelta, Completion

API_ROOT = 'https://api.openai.com/v1'


def new_client() -> httpx.Client:
    return httpx.Client(timeout=httpx.Timeout(90, connect=15), follow_redirects=False, trust_env=False)


@contextmanager
def cancellable_client(cancellation):
    with new_client() as client:
        remove = cancellation.on_cancel(client.close)
        try:
            yield client
        finally:
            remove()


def upstream_error(status: int, payload: object) -> LLMServiceError:
    error = payload.get('error', {}) if isinstance(payload, dict) else {}
    code = error.get('code') if isinstance(error, dict) else None
    mapping = {
        'subscription_sharing_usage_limit_exceeded': LLMErrorCode.QUOTA_EXCEEDED,
        'subscription_sharing_usage_unavailable': LLMErrorCode.TEMPORARILY_UNAVAILABLE,
        'subscription_sharing_user_unavailable': LLMErrorCode.TEMPORARILY_UNAVAILABLE,
        'subscription_sharing_user_not_eligible': LLMErrorCode.NOT_ELIGIBLE,
        'subscription_sharing_unsupported_capability': LLMErrorCode.UNSUPPORTED_CAPABILITY,
        'subscription_sharing_invalid_user': LLMErrorCode.RECONNECT_REQUIRED,
        'chatpass_v2_scope_not_authorized': LLMErrorCode.PERMISSION_REQUIRED,
        'chatpass_v2_invalid_authorization_context': LLMErrorCode.PERMISSION_REQUIRED,
        'model_not_found': LLMErrorCode.MODEL_UNAVAILABLE,
    }
    selected = mapping.get(code)
    if selected is None:
        selected = {
            401: LLMErrorCode.RECONNECT_REQUIRED, 403: LLMErrorCode.PERMISSION_REQUIRED,
            404: LLMErrorCode.MODEL_UNAVAILABLE, 429: LLMErrorCode.RATE_LIMITED,
            500: LLMErrorCode.TEMPORARILY_UNAVAILABLE, 502: LLMErrorCode.TEMPORARILY_UNAVAILABLE,
            503: LLMErrorCode.TEMPORARILY_UNAVAILABLE, 504: LLMErrorCode.TIMEOUT,
        }.get(status, LLMErrorCode.REQUEST_REJECTED)
    safe = LLMServiceError.for_code(selected)
    # Preserve upstream HTTP status, but never copy arbitrary admission text.
    return LLMServiceError(status, safe.detail, code=selected)


def read_json(response: httpx.Response) -> dict:
    try:
        payload = response.json()
    except (ValueError, UnicodeError):
        payload = {}
    if response.status_code >= 300:
        raise upstream_error(response.status_code, payload)
    if not isinstance(payload, dict):
        raise LLMServiceError.for_code(LLMErrorCode.INVALID_RESPONSE)
    return payload


def _count(value) -> int | None:
    return value if type(value) is int and value >= 0 else None


class ChatGPTProvider:
    capabilities = ProviderCapabilities(streaming=True, supported_parameters=frozenset({"reasoning_effort"}))

    def generate(self, request: LLMRequest, context: ExecutionContext, *, credential: SecretStr,
                 cancellation: CancellationToken) -> LLMResult:
        stream = self.stream(request, context, credential=credential, cancellation=cancellation)
        try:
            for event in stream:
                if isinstance(event, Completion):
                    return event.result
        finally:
            stream.close()
        raise LLMServiceError.for_code(LLMErrorCode.INVALID_RESPONSE)

    def stream(self, request: LLMRequest, context: ExecutionContext, *, credential: SecretStr,
               cancellation: CancellationToken):
        self.capabilities.validate(request)
        cancellation.raise_if_cancelled()
        started = time.monotonic()
        body = {
            'model': context.selection.model,
            'input': [{'role': 'user', 'content': request.prompt}],
            'store': False, 'stream': True,
        }
        if request.parameters.reasoning_effort is not None:
            body['reasoning'] = {'effort': request.parameters.reasoning_effort}
        try:
            with cancellable_client(cancellation) as client, client.stream(
                'POST', API_ROOT + '/responses', json=body,
                headers={'Authorization': 'Bearer ' + credential.get_secret_value(), 'Accept': 'text/event-stream'},
            ) as response:
                remove_close = cancellation.on_cancel(response.close)
                if response.status_code >= 300:
                    response.read()
                    read_json(response)
                pending, text, completed = [], [], None
                size = 0
                for line in response.iter_lines():
                    cancellation.raise_if_cancelled()
                    size += len(line)
                    if size > 4_000_000:
                        raise LLMServiceError.for_code(LLMErrorCode.INVALID_RESPONSE)
                    if line.startswith('data:'):
                        pending.append(line[5:].lstrip())
                    elif not line and pending:
                        data = '\n'.join(pending)
                        pending.clear()
                        if data == '[DONE]':
                            continue  # [DONE] without response.completed is not success.
                        try:
                            event = json.loads(data)
                        except ValueError:
                            raise LLMServiceError.for_code(LLMErrorCode.INVALID_RESPONSE) from None
                        if not isinstance(event, dict):
                            raise LLMServiceError.for_code(LLMErrorCode.INVALID_RESPONSE)
                        kind = event.get('type')
                        if kind == 'response.output_text.delta':
                            if not isinstance(event.get('delta'), str):
                                raise LLMServiceError.for_code(LLMErrorCode.INVALID_RESPONSE)
                            text.append(event['delta'])
                            yield TextDelta(event['delta'])
                        elif kind in ('response.failed', 'error'):
                            failed = event.get('response', event)
                            error = failed.get('error', {}) if isinstance(failed, dict) else {}
                            code = error.get('code') if isinstance(error, dict) else None
                            status = 429 if code == 'subscription_sharing_usage_limit_exceeded' else (
                                503 if code in ('subscription_sharing_usage_unavailable', 'subscription_sharing_user_unavailable') else 502
                            )
                            raise upstream_error(status, {'error': error})
                        elif kind == 'response.incomplete':
                            raise LLMServiceError.for_code(LLMErrorCode.INVALID_RESPONSE)
                        elif kind == 'response.completed':
                            completed = event.get('response')
                            if not isinstance(completed, dict) or completed.get('status') != 'completed':
                                raise LLMServiceError.for_code(LLMErrorCode.INVALID_RESPONSE)
                            break
                cancellation.raise_if_cancelled()
                if completed is None:
                    raise LLMServiceError.for_code(LLMErrorCode.INVALID_RESPONSE)
                # Prefer canonical completed output; deltas are never persisted on failure.
                parts = [part['text'] for item in completed.get('output', []) if isinstance(item, dict)
                         for part in item.get('content', []) if isinstance(part, dict)
                         and part.get('type') == 'output_text' and isinstance(part.get('text'), str)]
                answer = ''.join(parts) if parts else ''.join(text)
                if not answer.strip():
                    raise LLMServiceError.for_code(LLMErrorCode.INVALID_RESPONSE)
                usage = completed.get('usage')
                usage = TokenUsage(_count(usage.get('input_tokens')), _count(usage.get('output_tokens')),
                                   _count(usage.get('total_tokens'))) if isinstance(usage, dict) else None
                model = completed.get('model')
                yield Completion(LLMResult(text=answer.strip(), provider='chatgpt', model=model if isinstance(model, str) else None,
                                 duration_seconds=time.monotonic() - started, usage=usage))
        except LLMServiceError:
            raise
        except httpx.TimeoutException:
            raise LLMServiceError.for_code(LLMErrorCode.TIMEOUT) from None
        except httpx.TransportError:
            raise LLMServiceError.for_code(LLMErrorCode.TEMPORARILY_UNAVAILABLE) from None
        except Exception:
            raise LLMServiceError.for_code(LLMErrorCode.INVALID_RESPONSE) from None
        finally:
            if 'remove_close' in locals():
                remove_close()
