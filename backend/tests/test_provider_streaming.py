"""Native streaming completion, partial failures and transport cancellation."""
from threading import Event
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from pydantic import SecretStr

from src.errors import LLMServiceError
from src.providers.contracts import CancellationToken, Completion, ExecutionContext, LLMRequest, ModelSelection, TextDelta
from src.providers.gemini import GeminiProvider


class ProviderStreamingTests(unittest.TestCase):
    def setUp(self):
        self.factory = self.enterContext(patch('src.providers.gemini.genai.Client'))
        self.client = MagicMock()
        self.factory.return_value.__enter__.return_value = self.client
        self.context = ExecutionContext(ModelSelection('gemini','configured-model'))

    def stream(self):
        return GeminiProvider().stream(LLMRequest('test'), self.context, credential=SecretStr('fake-key'), cancellation=CancellationToken())

    def test_gemini_stream_requires_stop_and_reports_final_metadata(self):
        def chunks():
            yield SimpleNamespace(text='Hello ', model_version='actual-version', usage_metadata=None, candidates=[])
            yield SimpleNamespace(text='world', model_version='actual-version', usage_metadata=SimpleNamespace(prompt_token_count=2,candidates_token_count=3,total_token_count=5), candidates=[SimpleNamespace(finish_reason='STOP')])
        self.client.models.generate_content_stream.return_value = chunks()
        events = list(self.stream())
        self.assertTrue(all(isinstance(event,TextDelta) for event in events[:-1]))
        self.assertIsInstance(events[-1], Completion)
        self.assertEqual(events[-1].result.text, 'Hello world')
        self.assertEqual(events[-1].result.usage.total_tokens, 5)
        self.assertEqual(events[-1].result.model, 'actual-version')
        self.factory.return_value.__exit__.assert_called_once()

    def test_incomplete_native_stream_is_not_success(self):
        def chunks():
            yield SimpleNamespace(text='Partial', model_version=None, usage_metadata=None, candidates=[SimpleNamespace(finish_reason='MAX_TOKENS')])
        self.client.models.generate_content_stream.return_value = chunks()
        events = self.stream()
        self.assertIsInstance(next(events), TextDelta)
        with self.assertRaises(LLMServiceError): list(events)
        self.assertEqual(self.client.models.generate_content_stream.call_count, 1)

    def test_cancellation_closes_registered_transport(self):
        cancellation = CancellationToken()
        closed = Event()
        remove = cancellation.on_cancel(closed.set)
        cancellation.cancel()
        self.assertTrue(closed.wait(1))
        remove()
        with self.assertRaises(LLMServiceError): cancellation.raise_if_cancelled()
