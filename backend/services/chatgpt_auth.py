"""Single local runtime for account registrations, loopback OAuth and plan checks."""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from functools import lru_cache
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import re
import secrets
from threading import RLock, Lock, Thread, Timer
import time
from urllib.parse import parse_qs, urlencode, urlparse
from uuid import uuid4
import base64

from pydantic import SecretStr

from backend.services.chatgpt_oauth import OpenAIOAuth, OAuthTokenError, PLAN_SCOPE, RESOURCE, SCOPES, parse_tokens
from backend.services.chatgpt_storage import CredentialVault, RegistrationStore
from src.config import settings
from src.errors import LLMErrorCode, LLMServiceError
from src.llm import generate_llm, llm_task
from src.providers.chatgpt import API_ROOT, new_client, read_json
from src.providers.contracts import CancellationToken, CredentialRef, ExecutionContext, GenerationParameters, LLMRequest, ModelSelection


def safe_text(value, maximum=160):
    return ''.join(char for char in value if ord(char) >= 32)[:maximum] if isinstance(value, str) else ''


@dataclass(repr=False)
class Pending:
    owner: str
    connection_id: str | None
    client_id: str | None
    generation: int
    state: str = field(default_factory=lambda: secrets.token_urlsafe(32))
    nonce: str = field(default_factory=lambda: secrets.token_urlsafe(32))
    verifier: str = field(default_factory=lambda: secrets.token_urlsafe(64))
    ticket: str = field(default_factory=lambda: secrets.token_urlsafe(32))
    expires_at: float = field(default_factory=lambda: time.time() + 300)
    id: str = field(default_factory=lambda: uuid4().hex)
    consumed: bool = False
    launched: bool = False
    cancelled: bool = False
    status: str = 'waiting'
    server: ThreadingHTTPServer | None = None
    server_thread: Thread | None = None
    timer: Timer | None = None
    redirect_uri: str = ''
    authorization_url: str = ''

    def close(self):
        if self.timer:
            self.timer.cancel()
        if self.server:
            if self.server_thread and self.server_thread.is_alive():
                self.server.shutdown()
            self.server.server_close()


class ChatGPTConnections:
    def __init__(self, root=None, *, vault_factory=CredentialVault, oauth=None):
        self.store = RegistrationStore(root if root is not None else settings.chatgpt_runtime_dir)
        self.vault = vault_factory(self.store.host_id)
        self.oauth = oauth or OpenAIOAuth()
        self.lock = RLock()
        self.refresh_locks = {}
        self.check_locks = {}
        self.generations = {}
        self.catalogs = {}
        self.checked = {}
        self.inflight = {}
        self.logging_out = set()
        self.pending: Pending | None = None
        self.last_error = None
        self.closed = False

    def _profile(self, connection_id):
        profile = self.store.profiles.get(connection_id)
        if profile is None:
            raise LLMServiceError(404, 'ChatGPT connection was not found.')
        return profile

    def _valid(self, pending):
        return (not self.closed and self.pending is pending and not pending.cancelled
                and self.generations.get(pending.connection_id, 0) == pending.generation)

    def status(self, owner):
        with self.lock:
            profiles = []
            for key, profile in self.store.profiles.items():
                tokens = None if profile.get('signed_out', True) else self.vault.get(key)
                if tokens and PLAN_SCOPE in tokens.scopes and tokens.expires_at <= time.time() + 60 and not tokens.refresh:
                    tokens = None
                connected = bool(tokens and tokens.access)
                permission = bool(tokens and PLAN_SCOPE in tokens.scopes)
                state = ('connected' if permission else 'permission_required') if tokens else 'reconnect_required'
                profiles.append({
                    'id': key, 'label': profile.get('email') or profile.get('name') or 'Đăng ký chưa hoàn tất',
                    'state': state, 'plan_enabled': permission, 'identity_connected': connected or bool(tokens and tokens.id_token),
                    'catalog_checked': key in self.catalogs,
                    'inference_checked': key in self.checked, 'last_check': self.checked.get(key),
                    'welcome_pending': permission and not profile.get('welcome_ack', False),
                })
            pending = self.pending if self.pending and self.pending.owner == owner else None
            return {'profiles': profiles, 'active_connection_id': self.store.active_id,
                    'storage_mode': self.vault.mode, 'error': self.last_error,
                    'pending': {'id': pending.id, 'state': pending.status, 'expires_at': pending.expires_at} if pending else None}

    def start(self, owner, connection_id=None, *, consent=False):
        metadata = self.oauth.discovery()  # Discover before binding a listener.
        with self.lock:
            profile = self._profile(connection_id) if connection_id else None
            if connection_id in self.logging_out:
                raise LLMServiceError(409, 'ChatGPT sign-out is in progress.')
            if self.closed:
                raise LLMServiceError.for_code(LLMErrorCode.TEMPORARILY_UNAVAILABLE)
            old = self.pending
            if old and old.owner != owner:
                raise LLMServiceError(409, 'Another ChatGPT sign-in is in progress.')
            if old:
                old.cancelled = True
            pending = Pending(owner, connection_id, profile['client_id'] if profile else None,
                              self.generations.get(connection_id, 0))
            self.pending = pending
            self.last_error = None
        if old:
            old.close()
        manager = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass  # Never log callback query strings/codes.

            def do_GET(self):
                outcome = False
                try:
                    parsed = urlparse(self.path)
                    if (parsed.path != '/auth/callback' or len(self.path) > 16384
                            or self.headers.get('Host') != f'127.0.0.1:{self.server.server_port}'):
                        raise ValueError('Invalid callback')
                    query = parse_qs(parsed.query, keep_blank_values=True, max_num_fields=16)
                    if any(len(values) != 1 for values in query.values()):
                        raise ValueError('Duplicate callback parameter')
                    outcome = manager.callback(pending, {key: values[0] for key, values in query.items()})
                except Exception:
                    pass
                message = ('Đăng nhập đã hoàn tất. Bạn có thể đóng tab này và trở lại YourNote.' if outcome else
                           'Không thể hoàn tất đăng nhập. Trở lại YourNote để xem trạng thái và thử lại.')
                body = message.encode('utf-8')
                self.send_response(200 if outcome else 400)
                self.send_header('Content-Type', 'text/plain; charset=utf-8')
                self.send_header('Content-Length', str(len(body)))
                self.send_header('Cache-Control', 'no-store')
                self.send_header('Referrer-Policy', 'no-referrer')
                self.send_header('Content-Security-Policy', "default-src 'none'; frame-ancestors 'none'")
                self.end_headers()
                self.wfile.write(body)
                if pending.consumed:
                    Thread(target=pending.close, daemon=True).start()

        try:
            server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
            server.daemon_threads = True
            pending.server = server
            pending.redirect_uri = f'http://127.0.0.1:{server.server_port}/auth/callback'
            challenge = base64.urlsafe_b64encode(hashlib.sha256(pending.verifier.encode()).digest()).decode().rstrip('=')
            fields = {'client_id': pending.client_id or 'dynamic_agent_client', 'ext_agent_host_id': self.store.host_id,
                      'response_type': 'code', 'redirect_uri': pending.redirect_uri, 'scope': SCOPES, 'resource': RESOURCE,
                      'state': pending.state, 'nonce': pending.nonce, 'code_challenge_method': 'S256', 'code_challenge': challenge}
            if profile is None:
                fields['agent_name_hint'] = 'YourNote'
            elif profile.get('email'):
                fields['login_hint'] = profile['email']
            # No ID-token hint leaves the authorization URL entirely free of tokens.
            if consent:
                fields['prompt'] = 'consent'
            pending.authorization_url = metadata['authorization_endpoint'] + '?' + urlencode(fields)
            pending.server_thread = Thread(target=server.serve_forever, kwargs={'poll_interval': .1}, daemon=True)
            pending.server_thread.start()
            pending.timer = Timer(300, self.expire, args=(pending,))
            pending.timer.daemon = True
            pending.timer.start()
            return {'launch_path': '/api/ai/chatgpt/sign-in/launch?ticket=' + pending.ticket}
        except Exception:
            self.cancel(owner)
            raise LLMServiceError(503, 'Unable to start the local ChatGPT callback listener.') from None

    def launch(self, owner, ticket):
        with self.lock:
            pending = self.pending
            if (not pending or pending.owner != owner or pending.cancelled or pending.launched
                    or pending.expires_at <= time.time() or not secrets.compare_digest(pending.ticket, ticket)):
                raise LLMServiceError(400, 'ChatGPT sign-in could not be verified.')
            pending.launched = True
            return pending.authorization_url

    def expire(self, pending):
        with self.lock:
            if self.pending is pending:
                pending.cancelled = True
                self.pending = None
                self.last_error = 'ChatGPT sign-in expired. Please try again.'
        pending.close()

    def cancel(self, owner):
        with self.lock:
            pending = self.pending
            if pending and pending.owner == owner:
                pending.cancelled = True
                self.pending = None
            else:
                pending = None
        if pending:
            pending.close()

    def callback(self, pending, query):
        with self.lock:
            if (not self._valid(pending) or pending.consumed or pending.expires_at <= time.time()
                    or not secrets.compare_digest(query.get('state', ''), pending.state)):
                raise LLMServiceError(400, 'ChatGPT sign-in could not be verified.')
            pending.consumed = True
            pending.status = 'exchanging'
        try:
            if query.get('error'):
                raise LLMServiceError(400, 'ChatGPT sign-in was not completed.')
            code = query.get('code')
            client_id = query.get('client_id') or pending.client_id
            if not code or not client_id or client_id == 'dynamic_agent_client' or not re.fullmatch(r'[A-Za-z0-9_-]{1,256}', client_id):
                raise LLMServiceError(400, 'ChatGPT registration is incomplete.')
            if pending.client_id and client_id != pending.client_id:
                raise LLMServiceError(400, 'ChatGPT sign-in could not be verified.')
            with self.lock:
                if not self._valid(pending):
                    raise LLMServiceError.for_code(LLMErrorCode.CANCELLED)
                if pending.connection_id is None:
                    pending.connection_id = uuid4().hex
                    pending.generation = 0
                    self.store.profiles[pending.connection_id] = {'client_id': client_id, 'signed_out': True}
                    self.store.save()  # Retain registration even if code exchange later fails.
            data = self.oauth.exchange({'grant_type': 'authorization_code', 'client_id': client_id, 'code': code,
                                        'code_verifier': pending.verifier, 'redirect_uri': pending.redirect_uri, 'resource': RESOURCE})
            tokens = parse_tokens(data)
            if not tokens.id_token:
                raise LLMServiceError.for_code(LLMErrorCode.RECONNECT_REQUIRED)
            claims = self.oauth.verify_identity(tokens.id_token, client_id, pending.nonce)
            with self.lock:
                if not self._valid(pending):
                    raise LLMServiceError.for_code(LLMErrorCode.CANCELLED)
                profile = self._profile(pending.connection_id)
                if profile.get('subject') and profile['subject'] != claims['sub']:
                    raise LLMServiceError.for_code(LLMErrorCode.RECONNECT_REQUIRED)
                previous_profile = dict(profile)
                previous_active = self.store.active_id
                previous_tokens = self.vault.get(pending.connection_id)
                try:
                    self.vault.set(pending.connection_id, tokens)
                    profile.update(subject=claims['sub'], email=safe_text(claims.get('email')),
                                   name=safe_text(claims.get('name')), signed_out=False)
                    self.store.active_id = pending.connection_id
                    self.store.save()
                except Exception:
                    self.store.profiles[pending.connection_id] = previous_profile
                    self.store.active_id = previous_active
                    if previous_tokens:
                        self.vault.set(pending.connection_id, previous_tokens)
                    else:
                        self.vault.delete(pending.connection_id)
                    raise LLMServiceError.for_code(LLMErrorCode.TEMPORARILY_UNAVAILABLE) from None
                self.generations[pending.connection_id] = self.generations.get(pending.connection_id, 0) + 1
                self.catalogs.pop(pending.connection_id, None)
                self.checked.pop(pending.connection_id, None)
                self.pending = None
                self.last_error = None
            return True
        except Exception as exc:
            with self.lock:
                if self.pending is pending:
                    self.pending = None
                    self.last_error = exc.detail if isinstance(exc, LLMServiceError) else 'ChatGPT sign-in failed. Please try again.'
            return False

    def access(self, connection_id):
        with self.lock:
            refresh_lock = self.refresh_locks.setdefault(connection_id, Lock())
        with refresh_lock:
            with self.lock:
                profile = dict(self._profile(connection_id))
                generation = self.generations.get(connection_id, 0)
                tokens = None if profile.get('signed_out', True) else self.vault.get(connection_id)
                if self.closed or tokens is None or connection_id in self.logging_out:
                    raise LLMServiceError.for_code(LLMErrorCode.RECONNECT_REQUIRED)
                if PLAN_SCOPE not in tokens.scopes:
                    raise LLMServiceError.for_code(LLMErrorCode.PERMISSION_REQUIRED)
                if tokens.expires_at > time.time() + 60:
                    return SecretStr(tokens.access)
            if not tokens.refresh:
                raise LLMServiceError.for_code(LLMErrorCode.RECONNECT_REQUIRED)
            try:
                data = self.oauth.exchange({'grant_type': 'refresh_token', 'client_id': profile['client_id'],
                                            'refresh_token': tokens.refresh, 'resource': RESOURCE})
                updated = parse_tokens(data, tokens)
                if data.get('id_token'):
                    claims = self.oauth.verify_identity(data['id_token'], profile['client_id'], None)
                    if claims['sub'] != profile['subject']:
                        raise OAuthTokenError(True)
            except OAuthTokenError as exc:
                if exc.terminal:
                    with self.lock:
                        if self.generations.get(connection_id, 0) == generation:
                            self._disable(connection_id)
                raise
            with self.lock:
                if (self.closed or self.generations.get(connection_id, 0) != generation
                        or self._profile(connection_id).get('signed_out')):
                    raise LLMServiceError.for_code(LLMErrorCode.RECONNECT_REQUIRED)
                self.vault.set(connection_id, updated)
                if PLAN_SCOPE not in updated.scopes:
                    self.catalogs.pop(connection_id, None)
                    self.checked.pop(connection_id, None)
                    raise LLMServiceError.for_code(LLMErrorCode.PERMISSION_REQUIRED)
                return SecretStr(updated.access)

    def _disable(self, connection_id):
        self.generations[connection_id] = self.generations.get(connection_id, 0) + 1
        self._profile(connection_id)['signed_out'] = True
        for token in self.inflight.get(connection_id, []):
            token.cancel()
        self.vault.delete(connection_id)
        self.catalogs.pop(connection_id, None)
        self.checked.pop(connection_id, None)
        self.store.save()

    def catalog(self, connection_id):
        with self.lock:
            generation = self.generations.get(connection_id, 0)
        credential = self.access(connection_id)
        try:
            with new_client() as client:
                data = read_json(client.get(API_ROOT + '/models', headers={'Authorization': 'Bearer ' + credential.get_secret_value()}))
            if not isinstance(data.get('models'), list):
                raise ValueError('Missing catalog')
            models = []
            seen = set()
            for model in data['models']:
                if not isinstance(model, dict) or model.get('visibility') != 'list':
                    continue
                slug, label = model.get('slug'), model.get('display_name')
                ModelSelection('chatgpt', slug)
                if not isinstance(label, str) or not label.strip():
                    raise ValueError('Missing model name')
                if slug not in seen:
                    from src.providers.contracts import REASONING_EFFORTS
                    # Only expose capabilities explicitly advertised by the catalog.
                    advertised = model.get('supported_reasoning_levels', [])
                    levels = {item.get('effort') for item in advertised if isinstance(item, dict) and isinstance(item.get('effort'), str)} if isinstance(advertised, list) else set()
                    levels = [level for level in REASONING_EFFORTS if level in levels]
                    entry = {'slug': slug, 'display_name': safe_text(label)}
                    if levels:
                        entry['supported_reasoning_levels'] = levels
                        default = model.get('default_reasoning_level')
                        if default in levels:
                            entry['default_reasoning_level'] = default
                    models.append(entry)
                    seen.add(slug)
            with self.lock:
                if self.closed or self.generations.get(connection_id, 0) != generation or self._profile(connection_id).get('signed_out'):
                    raise LLMServiceError.for_code(LLMErrorCode.RECONNECT_REQUIRED)
                self.catalogs[connection_id] = models
            return {'models': models}
        except LLMServiceError:
            raise
        except Exception:
            raise LLMServiceError.for_code(LLMErrorCode.INVALID_RESPONSE) from None

    def check(self, connection_id, model):
        with self.lock:
            check_lock = self.check_locks.setdefault(connection_id, Lock())
        if not check_lock.acquire(blocking=False):
            raise LLMServiceError(409, 'ChatGPT connection check is already running.')
        try:
            return self._check(connection_id, model)
        finally:
            check_lock.release()

    def _check(self, connection_id, model):
        # Validate against a fresh account-specific catalog, no inference fallback.
        catalog = self.catalog(connection_id)['models']
        if model not in {entry['slug'] for entry in catalog}:
            raise LLMServiceError.for_code(LLMErrorCode.MODEL_UNAVAILABLE)
        cancellation = CancellationToken()
        with self.lock:
            generation = self.generations.get(connection_id, 0)
            self.inflight.setdefault(connection_id, []).append(cancellation)
        try:
            execution = ExecutionContext(ModelSelection('chatgpt', model), CredentialRef(connection_id), parameters=GenerationParameters())
            with llm_task(execution, credential_resolver=lambda ref: self.access(ref.id), cancellation=cancellation):
                result = generate_llm(LLMRequest('Reply with exactly: YourNote connection works.'))
            with self.lock:
                if self.closed or self.generations.get(connection_id, 0) != generation or self._profile(connection_id).get('signed_out'):
                    raise LLMServiceError.for_code(LLMErrorCode.RECONNECT_REQUIRED)
                verified = {'model': model, 'actual_model': result.model, 'checked_at': time.time(),
                            'duration_seconds': result.duration_seconds, 'usage': asdict(result.usage) if result.usage else None}
                self.checked[connection_id] = verified
            return verified
        finally:
            with self.lock:
                self.inflight.get(connection_id, []).remove(cancellation)

    @contextmanager
    def bind_task(self, connection_id, cancellation):
        """Bind an operation to this exact registration epoch, never the active UI profile."""
        with self.lock:
            self._profile(connection_id)
            generation = self.generations.get(connection_id, 0)
            self.inflight.setdefault(connection_id, []).append(cancellation)
        def resolve(reference):
            def validate():
                if (reference.id != connection_id or self.closed
                        or self.generations.get(connection_id, 0) != generation
                        or self._profile(connection_id).get('signed_out') or connection_id in self.logging_out):
                    raise LLMServiceError.for_code(LLMErrorCode.RECONNECT_REQUIRED)
            with self.lock:
                validate()
            cancellation.raise_if_cancelled()
            secret = self.access(connection_id)
            with self.lock:
                validate()
            cancellation.raise_if_cancelled()
            return secret
        try:
            yield resolve
        finally:
            with self.lock:
                self.inflight[connection_id].remove(cancellation)

    def select(self, connection_id):
        with self.lock:
            self._profile(connection_id)
            self.store.active_id = connection_id
            self.store.save()

    def acknowledge(self, connection_id):
        with self.lock:
            self._profile(connection_id)['welcome_ack'] = True
            self.store.save()

    def logout(self, connection_id):
        with self.lock:
            self._profile(connection_id)
            if connection_id in self.logging_out:
                raise LLMServiceError(409, 'ChatGPT sign-out is in progress.')
            self.logging_out.add(connection_id)
            refresh_lock = self.refresh_locks.setdefault(connection_id, Lock())
            for token in self.inflight.get(connection_id, []):
                token.cancel()
            pending = self.pending if self.pending and self.pending.connection_id == connection_id else None
            if pending:
                pending.cancelled = True
                self.pending = None
        try:
            if pending:
                pending.close()
            # Let an already-running rotation finish, then revoke the newest token.
            # No new access or reauthorization for this profile can start meanwhile.
            with refresh_lock:
                with self.lock:
                    profile = self._profile(connection_id)
                    tokens = None if profile.get('signed_out', True) else self.vault.get(connection_id)
                    client_id = profile['client_id']
                    self.generations[connection_id] = self.generations.get(connection_id, 0) + 1
                    profile['signed_out'] = True
                    self.store.save()
                remote = self.oauth.revoke(client_id, tokens.refresh) if tokens and tokens.refresh else False
                with self.lock:
                    local = self.vault.delete(connection_id)
                    self.catalogs.pop(connection_id, None)
                    self.checked.pop(connection_id, None)
                return {'local_signed_out': True, 'remote_revocation_confirmed': remote, 'keyring_cleanup_confirmed': local}
        finally:
            with self.lock:
                self.logging_out.discard(connection_id)

    def close(self):
        with self.lock:
            self.closed = True
            pending, self.pending = self.pending, None
            if pending:
                pending.cancelled = True
            for tokens in self.inflight.values():
                for token in tokens:
                    token.cancel()
        if pending:
            pending.close()
        self.vault.close()
        self.store.close()


_initialization_lock = Lock()


@lru_cache(maxsize=1)
def _cached_manager():
    return ChatGPTConnections()


def get_manager():
    # lru_cache alone permits duplicate constructor calls on concurrent misses.
    with _initialization_lock:
        return _cached_manager()


def shutdown():
    with _initialization_lock:
        if _cached_manager.cache_info().currsize:
            _cached_manager().close()
            _cached_manager.cache_clear()
