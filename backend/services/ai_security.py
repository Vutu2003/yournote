"""Loopback-only browser sessions and CSRF protection for credential endpoints."""
from dataclasses import dataclass
import ipaddress
import secrets
from threading import Lock
import time

from fastapi import HTTPException, Request, Response

COOKIE = 'yournote_ai_session'
ORIGINS = {'http://127.0.0.1:5173', 'http://localhost:5173',
           'http://127.0.0.1:4173', 'http://localhost:4173',
           'http://127.0.0.1:8000', 'http://localhost:8000'}


@dataclass
class BrowserSession:
    id: str
    csrf: str
    expires_at: float


_lock = Lock()
_sessions: dict[str, BrowserSession] = {}


def require_local(request: Request) -> None:
    try:
        if not request.client or not ipaddress.ip_address(request.client.host).is_loopback:
            raise ValueError('Remote peer')
        host = request.url.hostname
        if host not in ('127.0.0.1', 'localhost', '::1'):
            raise ValueError('Untrusted Host')
        origin = request.headers.get('origin')
        if origin is not None and origin not in ORIGINS:
            raise ValueError('Untrusted Origin')
        if request.headers.get('sec-fetch-site') == 'cross-site':
            raise ValueError('Cross-site request')
        if request.headers.get('x-yournote-local') != '1':
            raise ValueError('Missing app header')
    except ValueError:
        raise HTTPException(403, 'Open AI connections from the local YourNote app.') from None


def session(request: Request, *, mutation=False) -> BrowserSession:
    require_local(request)
    with _lock:
        value = _sessions.get(request.cookies.get(COOKIE, ''))
        if not value or value.expires_at <= time.time():
            raise HTTPException(401, 'Local AI session expired. Reopen settings.')
        if mutation and not secrets.compare_digest(request.headers.get('x-yournote-csrf', ''), value.csrf):
            raise HTTPException(403, 'Local AI session could not be verified.')
        value.expires_at = time.time() + 3600
        return value


def bootstrap(request: Request, response: Response) -> dict:
    require_local(request)
    with _lock:
        now = time.time()
        for key in list(_sessions):
            if _sessions[key].expires_at <= now:
                del _sessions[key]
        value = _sessions.get(request.cookies.get(COOKIE, ''))
        if value is None:
            if len(_sessions) >= 64:
                raise HTTPException(429, 'Too many local AI sessions.')
            value = BrowserSession(secrets.token_urlsafe(32), secrets.token_urlsafe(32), now + 3600)
            _sessions[value.id] = value
        response.set_cookie(COOKIE, value.id, httponly=True, samesite='strict', secure=False,
                            path='/api/ai', max_age=3600)
        response.headers['Cache-Control'] = 'no-store'
        return {'csrf': value.csrf}
