"""Task snapshots, completion gates, cancellation and persistence with no live data/AI."""
import asyncio
from contextlib import contextmanager
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient
from pydantic import SecretStr, TypeAdapter

from backend.main import app
from backend.schemas.tasks import TaskRequest
from backend.services import core_adapter
from backend.services.generation import TaskRegistry
from src.config import settings
from src.errors import LLMErrorCode, LLMServiceError
from src.providers.contracts import Completion, LLMResult, ProviderCapabilities, TextDelta, TokenUsage
from src.schemas import ChunkMetadata, RetrievedChunk


class FakeProvider:
    capabilities = ProviderCapabilities(streaming=True, supported_parameters=frozenset({'temperature', 'max_output_tokens', 'reasoning_effort'}))
    def __init__(self):
        self.output = 'Answer [S1]'
        self.calls = []
        self.wait = False
        self.entered = Event()
        self.failure = None
    def result(self, request, context):
        text = self.output() if callable(self.output) else self.output
        return LLMResult(text=text, provider=context.selection.provider, model='resolved-' + context.selection.model,
                         usage=TokenUsage(2, 3, 5), duration_seconds=.01)
    def generate(self, request, context, *, credential, cancellation):
        self.calls.append(context)
        return self.result(request, context)
    def stream(self, request, context, *, credential, cancellation):
        self.calls.append(context)
        yield TextDelta('Partial [S1]')
        self.entered.set()
        while self.wait:
            if cancellation.wait(.01):
                cancellation.raise_if_cancelled()
        if self.failure:
            raise self.failure
        yield Completion(self.result(request, context))


class FakeConnections:
    def __init__(self): self.active = True; self.catalog_models = ['alpha', 'beta']; self.levels = []
    def catalog(self, connection_id):
        if not self.active: raise LLMServiceError.for_code(LLMErrorCode.RECONNECT_REQUIRED)
        return {'models': [{'slug': model, 'display_name': model, 'supported_reasoning_levels': self.levels} for model in self.catalog_models]}
    @contextmanager
    def bind_task(self, connection_id, cancellation):
        def resolve(ref):
            if not self.active: raise LLMServiceError.for_code(LLMErrorCode.RECONNECT_REQUIRED)
            return SecretStr('fake-task-secret')
        yield resolve


class GenerationTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory(prefix='generation-test-')))
        self.enterContext(patch('backend.services.notebooks._database_path', return_value=self.root / 'notebooks.sqlite'))
        self.enterContext(patch.object(settings, 'gemini_api_key', 'fake-server-secret'))
        self.enterContext(patch.object(settings, 'llm_provider', 'gemini'))
        self.docs = [{'filename': name, 'document_id': name, 'pages': [1, 2], 'page_count': 2, 'chunk_count': 2} for name in ('course.pdf', 'other.pdf')]
        self.enterContext(patch('src.store.list_documents', return_value=self.docs))
        def chunks(*args, **kwargs):
            filters = kwargs.get('filters') or {}
            names = filters.get('filenames') or [filters.get('filename', 'course.pdf')]
            pages = [filters['page']] if filters.get('page') else [1, 2]
            return [RetrievedChunk(text=f'Course evidence {page}', score=0, metadata=ChunkMetadata(
                filename=name, document_id=name, source='/private/' + name, page=page, chunk_id=f'{name}:{page}:0',
            )) for name in names for page in pages]
        for target in ('src.rag.retrieve', 'src.rag.fetch_all_chunks', 'src.learning.retrieve', 'src.learning.fetch_all_chunks'):
            self.enterContext(patch(target, side_effect=chunks))
        self.registry = TaskRegistry()
        self.addCleanup(self.registry.close)
        self.enterContext(patch('backend.services.generation.get_registry', return_value=self.registry))
        self.provider = FakeProvider()
        self.enterContext(patch('src.llm.get_provider', return_value=self.provider))
        self.connections = FakeConnections()
        self.enterContext(patch('backend.services.chatgpt_auth.get_manager', return_value=self.connections))
        self.client = self.enterContext(TestClient(app, base_url='http://127.0.0.1:8000', client=('127.0.0.1', 12345)))
        self.headers = {'X-YourNote-Local': '1', 'Origin': 'http://127.0.0.1:5173'}
        csrf = self.client.get('/api/ai/session', headers=self.headers).json()['csrf']
        self.headers['X-YourNote-CSRF'] = csrf
        self.notebook = self.client.post('/api/notebooks', json={'title': 'Fixture'}).json()
        self.notebook['state']['document_filenames'] = ['course.pdf', 'other.pdf']
        self.notebook['state']['selected'] = ['course.pdf']
        self.client.put('/api/notebooks/' + self.notebook['id'], json={key:self.notebook[key] for key in ('title', 'icon', 'state')})

    def request(self, feature='chat', **updates):
        body = {'question': 'Explain', 'filenames': ['course.pdf']} if feature == 'chat' else {'filenames': ['course.pdf']}
        return {'id': str(uuid4()), 'notebook_id': self.notebook['id'], 'feature': feature,
                'model': {'provider': 'chatgpt', 'model': 'alpha', 'connection_id': 'test-connection'}, 'input': body, **updates}

    def events(self, request):
        response = self.client.post('/api/ai/tasks', headers=self.headers, json=request)
        self.assertEqual(response.status_code, 200, response.text)
        return [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith('data: ')]

    def collect(self, job):
        events = []
        until = time.monotonic() + 5
        while time.monotonic() < until:
            value = job.read()
            if value:
                events.append(value)
                if value['type'] in ('completed', 'error', 'cancelled'): return events
        self.fail('No terminal task event')

    def test_chat_emits_deltas_and_only_completed_result_has_metadata(self):
        request = self.request()
        events = self.events(request)
        self.assertIn('delta', [item['type'] for item in events])
        self.assertEqual(events[-1]['type'], 'completed')
        result = events[-1]['result']
        self.assertEqual(result['generation']['model'], 'resolved-alpha')
        self.assertEqual(result['generation']['request_id'], request['id'])
        self.assertEqual(result['generation']['usage']['total_tokens'], 5)
        self.assertNotIn('fake-task-secret', json.dumps(events))
        self.assertEqual(self.client.get('/api/notebooks/' + self.notebook['id']).json()['state']['chat'], [])
        state = self.notebook['state']
        state['chat'] = [result]
        saved = self.client.put('/api/notebooks/' + self.notebook['id'], json={'title':'Fixture','icon':'📓','state':state})
        self.assertEqual(saved.status_code, 200, saved.text)
        reloaded = self.client.get('/api/notebooks/' + self.notebook['id']).json()
        self.assertEqual(reloaded['state']['chat'][0]['generation'], result['generation'])

    def test_effort_is_validated_and_preserved_for_chat_and_map_reduce(self):
        for feature in ('chat', 'summary'):
            self.provider.calls.clear()
            self.connections.levels = ['low', 'high']
            request = self.request(feature)
            request['model']['reasoning_effort'] = 'high'
            if feature == 'summary':
                self.provider.output = json.dumps({'summary':'Summary','key_points':['Point']})
            with patch.object(settings, 'summarize_batch_size', 1):
                events = self.events(request)
            self.assertEqual(events[-1]['type'], 'completed', events[-1])
            self.assertEqual(events[-1]['result']['generation']['reasoning_effort'], 'high')
            self.assertEqual(len(self.provider.calls), 3 if feature == 'summary' else 1)
            self.assertTrue(all(call.parameters.reasoning_effort == 'high' for call in self.provider.calls))
        self.provider.calls.clear()
        self.connections.levels = []
        request['id'] = str(uuid4())
        events = self.events(request)
        self.assertEqual(events[-1]['code'], 'unsupported_capability')
        self.assertEqual(self.provider.calls, [])

    def test_source_replaced_during_generation_never_completes(self):
        from backend.schemas.api import ChatResponse
        self.docs[0]['document_version']='a'*64
        entered=Event();release=Event()
        def waiting(request,**kwargs):
            entered.set();release.wait(3)
            return ChatResponse(question=request.question,answer='Answer [S1]',citations=[{
                'source_index':1,'source_marker':'S1','filename':'course.pdf','page':1,'document_version':'a'*64}])
        with patch.object(core_adapter,'chat',side_effect=waiting):
            job=self.registry.start('owner',TypeAdapter(TaskRequest).validate_python(self.request()))
            self.assertTrue(entered.wait(3));self.docs[0]['document_version']='b'*64;release.set()
            events=self.collect(job)
        self.assertEqual(events[-1]['type'],'error');self.assertEqual(events[-1]['status'],409)
        self.assertNotIn('completed',[e['type'] for e in events]);self.registry.release(job)

    def test_client_version_mismatch_is_rejected_before_provider_call(self):
        self.docs[0]['document_version']='b'*64
        request=self.request();request['input']['document_versions']={'course.pdf':'a'*64}
        events=self.events(request)
        self.assertEqual(events[-1]['status'],409);self.assertEqual(self.provider.calls,[])

    def test_failure_after_partial_never_emits_completed_or_saves(self):
        self.provider.failure = LLMServiceError.for_code(LLMErrorCode.QUOTA_EXCEEDED)
        events = self.events(self.request())
        self.assertIn('delta', [event['type'] for event in events])
        self.assertEqual(events[-1]['type'], 'error')
        self.assertEqual(events[-1]['code'], 'quota_exceeded')
        self.assertNotIn('completed', [event['type'] for event in events])
        self.assertEqual(self.client.get('/api/notebooks/' + self.notebook['id']).json()['state']['chat'], [])

    def test_no_completion_from_provider_is_an_error(self):
        def unfinished(*args, **kwargs): yield TextDelta('Only a draft')
        with patch.object(self.provider, 'stream', side_effect=unfinished):
            events = self.events(self.request())
        self.assertEqual(events[-1]['type'], 'error')

    def test_registry_snapshots_choice_scope_and_does_not_hold_qdrant_lock_during_model_io(self):
        self.provider.wait = True
        request = TypeAdapter(TaskRequest).validate_python(self.request())
        job = self.registry.start('owner', request)
        self.assertTrue(self.provider.entered.wait(3))
        request.model.model = 'beta'
        request.input.filenames = ['other.pdf']
        acquired = core_adapter._core_lock.acquire(timeout=.5)
        self.assertTrue(acquired)
        if acquired: core_adapter._core_lock.release()
        self.provider.wait = False
        events = self.collect(job)
        self.assertEqual(events[-1]['result']['generation']['requested_model'], 'alpha')
        self.assertEqual(events[-1]['result']['generation']['source_filenames'], ['course.pdf'])
        self.registry.release(job)

    def test_cancel_wrong_owner_is_rejected_and_cancel_before_start_is_fenced(self):
        request = self.request()
        response = self.client.post('/api/ai/tasks/' + request['id'] + '/cancel', headers=self.headers, json={})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.post('/api/ai/tasks', headers=self.headers, json=request).status_code, 499)
        self.provider.wait = True
        parsed = TypeAdapter(TaskRequest).validate_python(self.request())
        job = self.registry.start('owner-a', parsed)
        self.assertTrue(self.provider.entered.wait(3))
        with self.assertRaises(LLMServiceError): self.registry.cancel('owner-b', parsed.id)
        self.registry.cancel('owner-a', parsed.id)
        self.assertEqual(self.collect(job)[-1]['type'], 'cancelled')
        self.registry.release(job)

    def test_server_connection_unavailable_and_removed_model_do_not_fall_back(self):
        for unavailable in ('connection', 'model'):
            self.connections.active = unavailable != 'connection'
            self.connections.catalog_models = [] if unavailable == 'model' else ['alpha']
            events = self.events(self.request())
            self.assertEqual(events[-1]['type'], 'error')
        self.assertEqual(self.provider.calls, [])

    def test_connection_removed_after_delta_cannot_complete(self):
        self.provider.wait = True
        request = TypeAdapter(TaskRequest).validate_python(self.request())
        job = self.registry.start('owner', request)
        self.assertTrue(self.provider.entered.wait(3))
        self.connections.active = False
        self.provider.wait = False
        events = self.collect(job)
        self.assertEqual(events[-1]['type'], 'error')
        self.assertEqual(events[-1]['code'], 'reconnect_required')
        self.assertNotIn('completed', [event['type'] for event in events])
        self.registry.release(job)

    def test_studio_tools_and_map_reduce_use_selected_model_and_hide_json_deltas(self):
        summary = json.dumps({'summary':'Summary','key_points':['Point']})
        quiz = json.dumps({'items':[{'question':'Which?','options':['A','B','C','D'],'correct_index':0,'explanation':'Because [S1]','source_markers':['S1']}]})
        cards = json.dumps({'cards':[{'front':'Question','back':'Answer','source_markers':['S1']}]})
        for feature, output in [('summary',summary), ('quiz',quiz), ('flashcards',cards)]:
            self.provider.calls.clear(); self.provider.output = output
            with patch.object(settings, 'summarize_batch_size', 1): events = self.events(self.request(feature))
            self.assertEqual(events[-1]['type'], 'completed', events[-1])
            self.assertNotIn('delta', [item['type'] for item in events])
            expected = 3 if feature == 'summary' else 1
            self.assertEqual(len(self.provider.calls), expected)
            self.assertTrue(all(call.selection.model == 'alpha' for call in self.provider.calls))
            self.assertEqual(len({call.request_id for call in self.provider.calls}), 1)
        outputs = iter(json.dumps({'root':{'label':'Topic','children':[{'label':'Concept','source_markers':markers}]}})
                       for markers in (['S1'],['S2'],['S1','S2']))
        self.provider.output = lambda: next(outputs)
        with patch.object(settings, 'mindmap_batch_size', 1): events = self.events(self.request('mindmap'))
        self.assertEqual(events[-1]['type'], 'completed', events[-1])
        self.assertEqual(events[-1]['result']['generation']['calls'], 3)

    def test_bad_json_and_unsupported_references_are_not_accepted(self):
        for output in ('not json', json.dumps({'summary':'Not supported [S999]','key_points':[]})):
            self.provider.output = output
            events = self.events(self.request('summary'))
            self.assertEqual(events[-1]['type'], 'error')
            self.assertNotIn('completed', [item['type'] for item in events])

    def test_call_limit_rejects_map_reduce_before_paid_invocation(self):
        with patch.object(settings, 'task_max_calls', 2), patch.object(settings, 'summarize_batch_size', 1):
            events = self.events(self.request('summary'))
        self.assertEqual(events[-1]['type'], 'error')
        self.assertEqual(self.provider.calls, [])

    def test_reading_uses_snapshot_and_metadata(self):
        from backend.schemas.reading import ReadingDocument
        info = ReadingDocument(document_id='course.pdf', filename='course.pdf', document_version='a'*64, page_count=2)
        request = self.request('reading', sources={'filenames':['course.pdf'],'pages':[]},
                               input={'document_id':'course.pdf','scope':'document','question':'Explain'})
        with patch('backend.services.reading.document', return_value=(info, Path('/unused'))):
            events = self.events(request)
        self.assertEqual(events[-1]['type'], 'completed', events[-1])
        self.assertEqual(events[-1]['result']['context']['filenames'], ['course.pdf'])
        self.assertEqual(events[-1]['result']['generation']['provider'], 'chatgpt')

    def test_disconnect_closes_task_and_draft_is_not_persisted(self):
        from backend.api.routes.tasks import run
        self.provider.wait = True
        fake = SimpleNamespace(client=SimpleNamespace(host='127.0.0.1'), url=SimpleNamespace(hostname='127.0.0.1'),
                               headers={key.lower():value for key,value in self.headers.items()},
                               cookies={'yournote_ai_session': self.client.cookies.get('yournote_ai_session')})
        disconnected = False
        async def is_disconnected(): return disconnected
        fake.is_disconnected = is_disconnected
        async def exercise():
            nonlocal disconnected
            body = TypeAdapter(TaskRequest).validate_python(self.request())
            response = await run(body, fake)
            stream = response.body_iterator
            await anext(stream)
            disconnected = True
            with self.assertRaises(StopAsyncIteration): await anext(stream)
            self.assertNotIn(body.id, self.registry.jobs)
        asyncio.run(exercise())
