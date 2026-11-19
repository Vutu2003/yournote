"""SSE transport for authenticated local model tasks and explicit cancellation."""
import asyncio
import json

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from backend.schemas.ai import EmptyRequest
from backend.schemas.tasks import TaskRequest
from backend.services import ai_security
from src.config import settings

router = APIRouter(prefix='/api/ai', tags=['AI tasks'])


@router.get('/options', summary='Read configured server model availability without credentials')
def options(request: Request):
    ai_security.session(request)
    return {'server': {'provider': 'gemini', 'model': settings.llm_model,
                       'configured': settings.llm_provider == 'gemini' and bool(settings.gemini_api_key)}}


@router.post('/tasks', summary='Run a source-scoped AI task as SSE', response_class=StreamingResponse,
             responses={200: {'content': {'text/event-stream': {}}}})
async def run(body: TaskRequest, request: Request):
    from backend.services.generation import get_registry
    browser = ai_security.session(request, mutation=True)
    registry = get_registry()
    job = registry.start(browser.id, body)
    async def events():
        try:
            while True:
                if await request.is_disconnected():
                    job.cancel()
                    return
                value = await asyncio.to_thread(job.read)
                if job.cancellation.cancelled:
                    value = {'type': 'cancelled' if job.reason != 'timeout' else 'error', 'code': job.reason,
                             'detail': 'AI task timed out.' if job.reason == 'timeout' else 'AI request was cancelled.',
                             'status': 504 if job.reason == 'timeout' else 499}
                if value is None:
                    yield ': heartbeat\n\n'
                    continue
                yield 'data: ' + json.dumps(value, ensure_ascii=False) + '\n\n'
                if value['type'] in ('completed', 'error', 'cancelled'):
                    return
        finally:
            registry.release(job)
    return StreamingResponse(events(), media_type='text/event-stream',
                             headers={'Cache-Control': 'no-store', 'X-Accel-Buffering': 'no'})


@router.post('/tasks/{task_id}/cancel', summary='Cancel an owned task or fence an upcoming request')
def cancel(task_id: str, body: EmptyRequest, request: Request):
    from backend.services.generation import get_registry
    browser = ai_security.session(request, mutation=True)
    get_registry().cancel(browser.id, task_id)
    return {'cancelled': True}
