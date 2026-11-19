"""Explicit local account connection only. No notebook inference changes in Phase 02."""
from fastapi import APIRouter, Request, Response
from fastapi.responses import RedirectResponse

from backend.schemas.ai import (
    CatalogResponse, CheckResult, ConnectionStatus, EmptyRequest, LaunchResponse,
    LogoutResponse, ModelCheckRequest, SessionResponse, SignInRequest,
)
from backend.schemas.api import ERROR_RESPONSES
from backend.services import ai_security

router = APIRouter(prefix='/api/ai', tags=['AI connections'], responses=ERROR_RESPONSES)


def manager():
    from backend.services.chatgpt_auth import get_manager
    return get_manager()


@router.get('/session', response_model=SessionResponse, summary='Open a local AI settings session')
def bootstrap(request: Request, response: Response):
    return ai_security.bootstrap(request, response)


@router.get('/chatgpt', response_model=ConnectionStatus, summary='Read safe ChatGPT connection status')
def status(request: Request, response: Response):
    browser = ai_security.session(request)
    response.headers['Cache-Control'] = 'no-store'
    return manager().status(browser.id)


@router.post('/chatgpt/sign-in', response_model=LaunchResponse, summary='Start explicit ChatGPT registration or reconnection')
def sign_in(body: SignInRequest, request: Request):
    browser = ai_security.session(request, mutation=True)
    return manager().start(browser.id, body.connection_id, consent=body.consent)


@router.get('/chatgpt/sign-in/launch', summary='Open the official ChatGPT authorization page')
def launch(ticket: str, request: Request):
    # Top-level navigation cannot send the app header. Cookie + one-use ticket,
    # loopback Host/peer and Fetch Metadata still bind it to the browser session.
    from starlette.requests import Request as StarletteRequest
    scope = dict(request.scope)
    scope['headers'] = [(key, value) for key, value in request.scope['headers'] if key != b'x-yournote-local']
    scope['headers'].append((b'x-yournote-local', b'1'))
    browser = ai_security.session(StarletteRequest(scope))
    return RedirectResponse(manager().launch(browser.id, ticket), status_code=303,
                            headers={'Cache-Control': 'no-store', 'Referrer-Policy': 'no-referrer'})


@router.post('/chatgpt/sign-in/cancel', response_model=ConnectionStatus, summary='Cancel the pending local sign-in')
def cancel(body: EmptyRequest, request: Request):
    browser = ai_security.session(request, mutation=True)
    manager().cancel(browser.id)
    return manager().status(browser.id)


@router.post('/chatgpt/profiles/{connection_id}/catalog', response_model=CatalogResponse, summary='Refresh this account model catalog without inference')
def catalog(connection_id: str, body: EmptyRequest, request: Request):
    ai_security.session(request, mutation=True)
    return manager().catalog(connection_id)


@router.post('/chatgpt/profiles/{connection_id}/check', response_model=CheckResult, summary='Run one user-requested short plan-usage check')
def check(connection_id: str, body: ModelCheckRequest, request: Request):
    ai_security.session(request, mutation=True)
    return manager().check(connection_id, body.model)


@router.post('/chatgpt/profiles/{connection_id}/logout', response_model=LogoutResponse, summary='Revoke the renewable session and clear local credentials')
def logout(connection_id: str, body: EmptyRequest, request: Request):
    ai_security.session(request, mutation=True)
    return manager().logout(connection_id)


@router.post('/chatgpt/profiles/{connection_id}/select', response_model=ConnectionStatus, summary='Select a saved ChatGPT registration')
def select(connection_id: str, body: EmptyRequest, request: Request):
    browser = ai_security.session(request, mutation=True)
    manager().select(connection_id)
    return manager().status(browser.id)


@router.post('/chatgpt/profiles/{connection_id}/notice', response_model=ConnectionStatus, summary='Acknowledge first-time ChatGPT plan usage')
def notice(connection_id: str, body: EmptyRequest, request: Request):
    browser = ai_security.session(request, mutation=True)
    manager().acknowledge(connection_id)
    return manager().status(browser.id)
