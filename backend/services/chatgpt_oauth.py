"""Public-client OAuth/OIDC operations against pinned official OpenAI origins."""
from __future__ import annotations

import secrets
from threading import RLock
import time
from urllib.parse import urlparse

import httpx

from backend.services.chatgpt_storage import Tokens
from src.errors import LLMErrorCode, LLMServiceError
from src.providers.chatgpt import read_json

ISSUER = 'https://auth.openai.com'
RESOURCE = 'https://api.openai.com/v1'
PLAN_SCOPE = 'chatgpt.tokens.use.direct'
SCOPES = 'openid profile email offline_access resource.invoke ' + PLAN_SCOPE


def new_client() -> httpx.Client:
    return httpx.Client(timeout=15, follow_redirects=False, trust_env=False)


class OAuthTokenError(LLMServiceError):
    def __init__(self, terminal: bool):
        safe = LLMServiceError.for_code(LLMErrorCode.RECONNECT_REQUIRED if terminal else LLMErrorCode.TEMPORARILY_UNAVAILABLE)
        super().__init__(safe.status_code, safe.detail, code=safe.code)
        self.terminal = terminal


class OpenAIOAuth:
    def __init__(self):
        self._metadata = None
        self._keys = None
        self._keys_at = 0
        self._lock = RLock()

    def discovery(self) -> dict:
        with self._lock:
            if self._metadata is None:
                try:
                    with new_client() as client:
                        data = read_json(client.get(ISSUER + '/.well-known/openid-configuration'))
                    if data.get('issuer') != ISSUER:
                        raise ValueError('Unexpected issuer')
                    for field in ('authorization_endpoint', 'token_endpoint', 'jwks_uri', 'revocation_endpoint'):
                        parsed = urlparse(data.get(field, ''))
                        if parsed.scheme != 'https' or parsed.netloc != 'auth.openai.com' or parsed.query or parsed.fragment:
                            raise ValueError('Unexpected discovery endpoint')
                    self._metadata = data
                except LLMServiceError:
                    raise
                except Exception:
                    raise LLMServiceError.for_code(LLMErrorCode.TEMPORARILY_UNAVAILABLE) from None
            return dict(self._metadata)

    def exchange(self, fields: dict) -> dict:
        try:
            with new_client() as client:
                response = client.post(self.discovery()['token_endpoint'], data=fields)
            data = response.json()
            if response.status_code >= 300:
                error = data.get('error') if isinstance(data, dict) else None
                terminal = error in {'invalid_grant', 'invalid_client', 'invalid_refresh_token', 'token_expired',
                                     'refresh_token_expired', 'refresh_token_invalidated', 'refresh_token_reused'}
                raise OAuthTokenError(terminal)
            if not isinstance(data, dict):
                raise ValueError('Invalid token response')
            return data
        except LLMServiceError:
            raise
        except Exception:
            raise LLMServiceError.for_code(LLMErrorCode.TEMPORARILY_UNAVAILABLE) from None

    def verify_identity(self, token: str, client_id: str, nonce: str | None) -> dict:
        import jwt
        try:
            header = jwt.get_unverified_header(token)
            if header.get('alg') != 'RS256' or not isinstance(header.get('kid'), str):
                raise ValueError('Unsupported signing key')
            with self._lock:
                for refresh in (False, True):
                    if refresh or self._keys is None or time.time() - self._keys_at > 300:
                        with new_client() as client:
                            self._keys = read_json(client.get(self.discovery()['jwks_uri']))['keys']
                        self._keys_at = time.time()
                    candidates = [key for key in self._keys if key.get('kid') == header['kid']
                                  and key.get('kty') == 'RSA' and key.get('use', 'sig') == 'sig'
                                  and key.get('alg', 'RS256') == 'RS256']
                    if candidates:
                        break
                if len(candidates) != 1:
                    raise ValueError('Unknown signing key')
                key = jwt.PyJWK.from_dict(candidates[0], algorithm='RS256').key
            claims = jwt.decode(token, key, algorithms=['RS256'], issuer=ISSUER, audience=client_id,
                                leeway=5, options={'require': ['iss', 'aud', 'sub', 'exp', 'iat']})
            if not isinstance(claims.get('sub'), str) or not claims['sub']:
                raise ValueError('Missing identity')
            if nonce is not None and (not isinstance(claims.get('nonce'), str) or not secrets.compare_digest(claims['nonce'], nonce)):
                raise ValueError('Invalid nonce')
            audience = claims['aud']
            if (isinstance(audience, list) and len(audience) > 1 and claims.get('azp') != client_id
                    or 'azp' in claims and claims['azp'] != client_id):
                raise ValueError('Invalid authorized party')
            return claims
        except LLMServiceError:
            raise
        except Exception:
            raise LLMServiceError.for_code(LLMErrorCode.RECONNECT_REQUIRED) from None

    def revoke(self, client_id: str, refresh: str) -> bool:
        # Bound retries; no logging of form data or provider bodies.
        for attempt in range(2):
            try:
                with new_client() as client:
                    response = client.post(self.discovery()['revocation_endpoint'], data={
                        'token': refresh, 'token_type_hint': 'refresh_token', 'client_id': client_id,
                    })
                if response.status_code == 200:
                    return True
                if response.status_code < 500:
                    return False
            except Exception:
                pass
            if attempt == 0:
                time.sleep(0.25)
        return False


def parse_tokens(data: dict, previous: Tokens | None = None) -> Tokens:
    import math
    try:
        scope = data.get('scope')
        scopes = frozenset(scope.split()) if isinstance(scope, str) else (previous.scopes if previous else frozenset())
        access = data.get('access_token', '')
        if not isinstance(access, str) or PLAN_SCOPE in scopes and not access:
            raise ValueError('Missing access token')
        if access and str(data.get('token_type', '')).lower() != 'bearer':
            raise ValueError('Unexpected token type')
        lifetime = float(data.get('expires_in', 0))
        if not math.isfinite(lifetime) or lifetime < 0 or (access and lifetime <= 0):
            raise ValueError('Invalid token expiry')
        refresh = data.get('refresh_token', previous.refresh if previous else None)
        identity = data.get('id_token', previous.id_token if previous else None)
        if any(value is not None and not isinstance(value, str) for value in (refresh, identity)):
            raise ValueError('Invalid token field')
        return Tokens(access, refresh, identity, time.time() + lifetime, scopes)
    except Exception:
        raise LLMServiceError.for_code(LLMErrorCode.INVALID_RESPONSE) from None
