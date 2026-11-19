"""OS-protected credentials or RAM only; manifests contain registration metadata only."""
from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
from pathlib import Path
from threading import RLock
from uuid import uuid4

from src.errors import LLMErrorCode, LLMServiceError


@dataclass(repr=False)
class Tokens:
    access: str = field(repr=False)
    refresh: str | None = field(default=None, repr=False)
    id_token: str | None = field(default=None, repr=False)
    expires_at: float = 0
    scopes: frozenset[str] = frozenset()

    def encode(self) -> str:
        return json.dumps({'access': self.access, 'refresh': self.refresh, 'id_token': self.id_token,
                           'expires_at': self.expires_at, 'scopes': sorted(self.scopes)})

    @classmethod
    def decode(cls, raw: str) -> Tokens:
        data = json.loads(raw)
        if not isinstance(data.get('access'), str) or not isinstance(data.get('scopes'), list):
            raise ValueError('Invalid protected credential record')
        return cls(data['access'], data.get('refresh'), data.get('id_token'), float(data['expires_at']), frozenset(data['scopes']))


class CredentialVault:
    def __init__(self, host_id: str):
        self._cache: dict[str, Tokens | None] = {}
        self._backend = None
        self._available = False
        self._lock = RLock()
        self._service = 'YourNote.ChatGPT.' + host_id
        # Reject alternate/plaintext file keyrings, including configurable chainers.
        try:
            import keyring
            backend = keyring.get_keyring()
            allowed = ('keyring.backends.SecretService', 'keyring.backends.macOS',
                       'keyring.backends.Windows', 'keyring.backends.kwallet')
            candidates = getattr(backend, 'backends', [backend])
            backend = next((item for item in candidates if type(item).__module__ in allowed and item.priority > 0), None)
            if backend is not None:
                probe = 'probe-' + uuid4().hex
                backend.set_password(self._service, probe, probe)
                if backend.get_password(self._service, probe) == probe:
                    self._backend = backend
                    self._available = True
                backend.delete_password(self._service, probe)
        except Exception:
            self._backend = None

    @property
    def mode(self) -> str:
        return 'keyring' if self._backend is not None and self._available else 'memory'

    def get(self, connection_id: str) -> Tokens | None:
        with self._lock:
            if connection_id not in self._cache:
                try:
                    raw = self._backend.get_password(self._service, connection_id) if self._backend else None
                    self._cache[connection_id] = Tokens.decode(raw) if raw else None
                except Exception:
                    self._cache[connection_id] = None
                    self._available = False
            return self._cache[connection_id]

    def set(self, connection_id: str, tokens: Tokens) -> None:
        with self._lock:
            self._cache[connection_id] = tokens
            if self._backend and self._available:
                try:
                    self._backend.set_password(self._service, connection_id, tokens.encode())
                except Exception:
                    # Explicitly reflected as memory mode in every public status.
                    self._available = False

    def delete(self, connection_id: str) -> bool:
        with self._lock:
            self._cache[connection_id] = None
            if self._backend:
                try:
                    if self._backend.get_password(self._service, connection_id) is not None:
                        self._backend.delete_password(self._service, connection_id)
                except Exception:
                    return False
            return True

    def close(self) -> None:
        with self._lock:
            self._cache.clear()


class RegistrationStore:
    def __init__(self, root: Path):
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(root, 0o700)
        self.root = root
        self._lockfile = (root / 'runtime.lock').open('a+b')
        os.chmod(root / 'runtime.lock', 0o600)
        try:
            if os.name == 'nt':
                import msvcrt
                self._lockfile.write(b'0')
                self._lockfile.flush()
                self._lockfile.seek(0)
                msvcrt.locking(self._lockfile.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self._lockfile, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self._lockfile.close()
            raise LLMServiceError(503, 'ChatGPT connection is already open in another process.') from None
        try:
            path = root / 'registrations.json'
            data = json.loads(path.read_text()) if path.exists() else {}
            self.host_id = data.get('host_id') or 'urn:uuid:' + str(uuid4())
            self.profiles = data.get('profiles', {})
            self.active_id = data.get('active_id')
            if not isinstance(self.profiles, dict) or not self.host_id.startswith('urn:uuid:'):
                raise ValueError('Invalid registration manifest')
            self.save()
        except Exception:
            self.close()
            raise LLMServiceError.for_code(LLMErrorCode.NOT_CONFIGURED) from None

    def save(self) -> None:
        # Only an explicit allowlist is written; Tokens never enter this manifest.
        allowed = ('client_id', 'subject', 'email', 'name', 'signed_out', 'welcome_ack')
        data = {'host_id': self.host_id, 'active_id': self.active_id,
                'profiles': {key: {name: value for name, value in profile.items() if name in allowed}
                             for key, profile in self.profiles.items()}}
        temporary = self.root / ('manifest-' + uuid4().hex + '.tmp')
        try:
            descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, 'w') as out:
                json.dump(data, out)
            os.replace(temporary, self.root / 'registrations.json')
        finally:
            temporary.unlink(missing_ok=True)

    def close(self) -> None:
        self._lockfile.close()
