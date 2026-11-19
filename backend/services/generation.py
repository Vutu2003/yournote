"""Bounded local tasks. Background work never writes notebook state."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from contextlib import nullcontext
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import lru_cache
from queue import Empty, Full, Queue
import re
from threading import Lock, RLock, Timer
import time

from backend.schemas.api import ChatResponse
from backend.schemas.generation import GenerationMetadata, ReportedUsage
from backend.schemas.tasks import ReadingTask
from backend.services import core_adapter, notebooks, reading
from src.config import settings
from src.errors import LLMErrorCode, LLMServiceError
from src.llm import llm_task
from src.providers.contracts import CancellationToken, CredentialRef, ExecutionContext, GenerationParameters, ModelSelection


@dataclass
class Job:
    request: object
    owner: str
    cancellation: CancellationToken = field(default_factory=CancellationToken)
    queue: Queue = field(default_factory=lambda: Queue(maxsize=128))
    terminal: bool = False
    lock: Lock = field(default_factory=Lock)
    timer: Timer | None = None
    future: object = None
    reason: str = 'cancelled'

    def cancel(self, reason='cancelled'):
        self.reason = reason
        self.cancellation.cancel()

    def emit(self, kind, **values):
        terminal = kind in ('completed', 'error', 'cancelled')
        while True:
            if not terminal:
                self.cancellation.raise_if_cancelled()
            with self.lock:
                if self.terminal:
                    return
                try:
                    self.queue.put_nowait({'type': kind, **values})
                    if terminal:
                        self.terminal = True
                    return
                except Full:
                    pass
            if self.cancellation.wait(.05):
                # A disconnected client no longer drains the queue.
                if terminal:
                    return
                self.cancellation.raise_if_cancelled()

    def read(self):
        try:
            return self.queue.get(timeout=.25)
        except Empty:
            return None


def task_sources(request):
    return request.sources if isinstance(request, ReadingTask) else request.input


def validate_result(result, sources, feature):
    allowed = set(sources.filenames)
    markers = {citation.source_marker for citation in result.citations}
    if len(markers) != len(result.citations):
        raise LLMServiceError.for_code(LLMErrorCode.INVALID_RESPONSE)
    for citation in result.citations:
        if citation.filename not in allowed or (sources.pages and citation.page not in sources.pages):
            raise LLMServiceError.for_code(LLMErrorCode.INVALID_RESPONSE)
        expected=sources.document_versions.get(citation.filename)
        if expected and citation.document_version!=expected:
            raise LLMServiceError.for_code(LLMErrorCode.INVALID_RESPONSE)
    if feature in ('comparison','report','graph'): return  # Research DTOs validate structured evidence, including on reload/export.
    dumped = result.model_dump(exclude={'generation'})
    def walk(value):
        if isinstance(value, str):
            if any('S' + marker not in markers for marker in re.findall(r'\[S([1-9][0-9]*)\]', value)):
                raise LLMServiceError.for_code(LLMErrorCode.INVALID_RESPONSE)
        elif isinstance(value, list):
            for item in value: walk(item)
        elif isinstance(value, dict):
            for key, item in value.items():
                if key not in ('citations', 'context', 'question', 'target'): walk(item)
    walk(dumped)
    if feature == 'summary' and not result.summary.strip():
        raise LLMServiceError.for_code(LLMErrorCode.INVALID_RESPONSE)
    if feature in ('quiz', 'flashcards'):
        items = result.items if feature == 'quiz' else result.cards
        if not items or any(not item.source_markers or not set(item.source_markers) <= markers for item in items):
            raise LLMServiceError.for_code(LLMErrorCode.INVALID_RESPONSE)


class TaskRegistry:
    def __init__(self):
        self.lock = RLock()
        self.jobs = {}
        self.futures = set()
        self.cancelled = {}
        self.pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix='yournote-ai')
        self.closed = False

    def start(self, owner, request):
        frozen = request.model_copy(deep=True)
        with self.lock:
            now = time.monotonic()
            self.cancelled = {key: until for key, until in self.cancelled.items() if until > now}
            if self.closed:
                raise LLMServiceError.for_code(LLMErrorCode.TEMPORARILY_UNAVAILABLE)
            if (owner, frozen.id) in self.cancelled:
                raise LLMServiceError.for_code(LLMErrorCode.CANCELLED)
            if frozen.id in self.jobs:
                raise LLMServiceError(409, 'This AI task ID has already been used.')
            if len(self.futures) >= 8:
                raise LLMServiceError(429, 'Too many AI tasks are active.')
            job = Job(frozen, owner)
            self.jobs[frozen.id] = job
            job.timer = Timer(settings.task_timeout_seconds, job.cancel, args=('timeout',))
            job.timer.daemon = True
            job.timer.start()
            job.future = self.pool.submit(self._run, job)
            self.futures.add(job.future)
            job.future.add_done_callback(self._finished)
            return job

    def _finished(self, future):
        with self.lock:
            self.futures.discard(future)

    def cancel(self, owner, identifier):
        with self.lock:
            job = self.jobs.get(identifier)
            if job is not None:
                if job.owner != owner:
                    raise LLMServiceError(404, 'AI task was not found.')
                job.cancel()
            else:
                if len(self.cancelled) >= 256:
                    self.cancelled.pop(next(iter(self.cancelled)))
                self.cancelled[(owner, identifier)] = time.monotonic() + 60

    def release(self, job):
        job.cancel()
        if job.future:
            job.future.cancel()
        if job.timer:
            job.timer.cancel()
        with self.lock:
            self.jobs.pop(job.request.id, None)
            if len(self.cancelled) >= 256:
                self.cancelled.pop(next(iter(self.cancelled)))
            self.cancelled[(job.owner, job.request.id)] = time.monotonic() + 60

    def _run(self, job):
        started = time.monotonic()
        request, cancellation = job.request, job.cancellation
        sources = task_sources(request)
        records = []
        def record(result):
            records.append({'model': result.model, 'usage': result.usage})
            job.emit('progress', stage='generating', calls=len(records))
        try:
            job.emit('started', task_id=request.id, notebook_id=request.notebook_id, feature=request.feature)
            workspace = notebooks.get_notebook(request.notebook_id)
            if not set(sources.filenames) <= set(workspace.state.document_filenames):
                raise core_adapter.AdapterError(409, 'Notebook sources have changed. Save and try again.')
            versions=core_adapter.current_versions(sources)
            sources.document_versions=dict(versions)
            from src.conversation import scoped_history
            history=scoped_history(workspace,sources,versions) if request.feature in ('chat','reading') else []
            selection = request.model
            manager = None
            if selection.provider == 'chatgpt':
                from backend.services.chatgpt_auth import get_manager
                manager = get_manager()
                catalog = manager.catalog(selection.connection_id)['models']
                selected_model = next((model for model in catalog if model['slug'] == selection.model), None)
                if selected_model is None:
                    raise LLMServiceError.for_code(LLMErrorCode.MODEL_UNAVAILABLE)
                binding = manager.bind_task(selection.connection_id, cancellation)
                if selection.reasoning_effort is not None and selection.reasoning_effort not in selected_model.get('supported_reasoning_levels', []):
                    raise LLMServiceError.for_code(LLMErrorCode.UNSUPPORTED_CAPABILITY)
                parameters = GenerationParameters(reasoning_effort=selection.reasoning_effort)
                reference = CredentialRef(selection.connection_id)
            else:
                if settings.llm_provider != 'gemini' or selection.model != settings.llm_model:
                    raise LLMServiceError.for_code(LLMErrorCode.MODEL_UNAVAILABLE)
                binding = nullcontext(None)
                parameters = GenerationParameters(temperature=settings.llm_temperature, max_output_tokens=settings.llm_max_new_tokens)
                reference = CredentialRef()
            execution = ExecutionContext(ModelSelection(selection.provider, selection.model), reference,
                                         request_id=request.id, parameters=parameters)
            with binding as resolver, llm_task(
                execution, credential_resolver=resolver, cancellation=cancellation,
                on_delta=(lambda text: job.emit('delta', text=text)) if request.feature in ('chat', 'reading') else None,
                on_result=record, max_calls=settings.task_max_calls,
            ):
                job.emit('progress', stage='preparing', calls=0)
                if request.feature == 'reading':
                    if request.input.scope == 'document':
                        info, _ = reading.document(request.notebook_id, request.input.document_id)
                        if sources.filenames != [info.filename] or sources.pages:
                            raise core_adapter.AdapterError(422, 'Reading source snapshot does not match the open PDF.')
                    result = reading.chat(request.notebook_id, request.input, filenames_snapshot=sources.filenames,history=history)
                elif request.feature in ('comparison','report','graph'):
                    result=getattr(core_adapter,request.feature)(request.input,progress=lambda **values:job.emit('progress',**values))
                elif request.feature=='chat':
                    result=core_adapter.chat(request.input,history=history)
                else:
                    result = getattr(core_adapter, request.feature)(request.input)
                cancellation.raise_if_cancelled()
                core_adapter._filters(sources)  # Reject a replacement while network generation was in flight.
                if not set(sources.filenames)<=set(notebooks.get_notebook(request.notebook_id).state.document_filenames):
                    raise core_adapter.AdapterError(409,'Notebook sources have changed. Save and try again.')
                validate_result(result, sources, request.feature)
                if manager:
                    resolver(reference)  # Recheck connection epoch before accepting the final result.
                models = list(dict.fromkeys(item['model'] for item in records if item['model']))
                usage = None
                if records:
                    counts = {}
                    for key in ('input_tokens', 'output_tokens', 'total_tokens'):
                        values = [getattr(item['usage'], key, None) for item in records]
                        counts[key] = sum(values) if all(value is not None for value in values) else None
                    if any(value is not None for value in counts.values()):
                        usage = ReportedUsage(**counts)
                result.generation = GenerationMetadata(
                    provider=selection.provider, requested_model=selection.model, reasoning_effort=selection.reasoning_effort,
                    model=models[0] if len(models) == 1 and all(item['model'] for item in records) else None,
                    actual_models=models, request_id=request.id, notebook_id=request.notebook_id,
                    source_versions=versions,source_filenames=list(sources.filenames), pages=list(sources.pages), calls=len(records),
                    created_at=datetime.now(timezone.utc).isoformat(), status='completed',
                    duration_seconds=time.monotonic() - started, usage=usage,
                )
                cancellation.raise_if_cancelled()
                job.emit('completed', result=result.model_dump(mode='json'))
        except Exception as exc:
            if cancellation.cancelled:
                job.emit('cancelled' if job.reason != 'timeout' else 'error',
                         code=job.reason, detail='AI task timed out.' if job.reason == 'timeout' else 'AI request was cancelled.',
                         status=504 if job.reason == 'timeout' else 499)
            elif isinstance(exc, (LLMServiceError, core_adapter.AdapterError)):
                job.emit('error', code=getattr(exc, 'code', LLMErrorCode.INVALID_REQUEST), detail=exc.detail, status=exc.status_code)
            else:
                safe = LLMServiceError.for_code(LLMErrorCode.INVALID_RESPONSE)
                job.emit('error', code=safe.code.value, detail=safe.detail, status=safe.status_code)
        finally:
            if job.timer:
                job.timer.cancel()

    def close(self):
        with self.lock:
            self.closed = True
            for job in self.jobs.values():
                job.cancel()
        self.pool.shutdown(wait=False, cancel_futures=True)


_registry_lock = Lock()


@lru_cache(maxsize=1)
def _cached_registry():
    return TaskRegistry()


def get_registry():
    with _registry_lock:
        return _cached_registry()


def shutdown():
    with _registry_lock:
        if _cached_registry.cache_info().currsize:
            _cached_registry().close()
            _cached_registry.cache_clear()
