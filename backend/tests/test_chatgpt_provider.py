"""Real HTTP/SSE parsing with MockTransport; no external requests or paid inference."""
import json
import unittest
from unittest.mock import patch

import httpx
from pydantic import SecretStr

from src.errors import LLMErrorCode, LLMServiceError
from src.providers.chatgpt import ChatGPTProvider
from src.providers.contracts import CancellationToken, ExecutionContext, GenerationParameters, LLMRequest, ModelSelection


def event(kind, **values):
    return 'data: ' + json.dumps({'type': kind, **values}) + '\n\n'


def success():
    return event('response.output_text.delta', delta='Partial ') + event('response.completed', response={
        'status': 'completed', 'model': 'actual-model',
        'output': [{'content': [{'type': 'output_text', 'text': 'Complete answer'}]}],
        'usage': {'input_tokens': 10, 'output_tokens': 2, 'total_tokens': 12},
    })


class ChatGPTProviderTests(unittest.TestCase):
    def setUp(self):
        self.requests = []
        self.response = httpx.Response(200, text=success())
        def transport(request):
            self.requests.append(request)
            return self.response
        self.enterContext(patch('src.providers.chatgpt.new_client', side_effect=lambda: httpx.Client(transport=httpx.MockTransport(transport))))
        self.provider = ChatGPTProvider()

    def invoke(self):
        return self.provider.generate(LLMRequest('test'), ExecutionContext(ModelSelection('chatgpt', 'allowed-model')),
                                      credential=SecretStr('access-sentinel'), cancellation=CancellationToken())

    def test_public_endpoint_body_and_completed_metadata(self):
        result = self.invoke()
        self.assertEqual(result.text, 'Complete answer')
        self.assertEqual(result.model, 'actual-model')
        self.assertEqual(result.usage.total_tokens, 12)
        request = self.requests[0]
        self.assertEqual(str(request.url), 'https://api.openai.com/v1/responses')
        self.assertEqual(request.headers['authorization'], 'Bearer access-sentinel')
        self.assertEqual(set(json.loads(request.content)), {'model', 'input', 'stream', 'store'})
        self.assertEqual(json.loads(request.content)['store'], False)
        self.assertEqual(json.loads(request.content)['stream'], True)
        self.assertNotIn('access-sentinel', repr(result))

    def test_explicit_reasoning_effort_is_forwarded_to_responses(self):
        parameters = GenerationParameters(reasoning_effort='high')
        self.provider.generate(LLMRequest('test', parameters=parameters),
                               ExecutionContext(ModelSelection('chatgpt', 'allowed-model'), parameters=parameters),
                               credential=SecretStr('fake-secret'), cancellation=CancellationToken())
        self.assertEqual(json.loads(self.requests[0].content)['reasoning'], {'effort': 'high'})

    def test_delta_http_200_and_done_are_not_success_without_completion(self):
        for body in (event('response.output_text.delta', delta='Unfinished'), 'data: [DONE]\n\n',
                     event('response.incomplete', response={'status': 'incomplete'}), 'data: invalid\n\n'):
            with self.subTest(body=body):
                self.response = httpx.Response(200, text=body)
                with self.assertRaises(LLMServiceError) as caught:
                    self.invoke()
                self.assertEqual(caught.exception.code, LLMErrorCode.INVALID_RESPONSE)

    def test_quota_failure_after_delta_does_not_return_partial_text(self):
        self.response = httpx.Response(200, text=event('response.output_text.delta', delta='Partial') +
            event('response.failed', response={'error': {'code': 'subscription_sharing_usage_limit_exceeded', 'message': 'access-sentinel'}}))
        with self.assertRaises(LLMServiceError) as caught:
            self.invoke()
        self.assertEqual(caught.exception.status_code, 429)
        self.assertEqual(caught.exception.code, LLMErrorCode.QUOTA_EXCEEDED)
        self.assertNotIn('access-sentinel', str(caught.exception))
        self.assertEqual(len(self.requests), 1)

    def test_admission_shapes_are_safe_and_not_retried(self):
        for status, data, expected in [
            (401, {'detail': 'access-sentinel'}, LLMErrorCode.RECONNECT_REQUIRED),
            (403, {'error': {'code': 'subscription_sharing_user_not_eligible'}}, LLMErrorCode.NOT_ELIGIBLE),
            (503, {'detail': 'upstream-private-body'}, LLMErrorCode.TEMPORARILY_UNAVAILABLE),
        ]:
            with self.subTest(status=status):
                self.response = httpx.Response(status, json=data)
                before = len(self.requests)
                with self.assertRaises(LLMServiceError) as caught:
                    self.invoke()
                self.assertEqual(caught.exception.status_code, status)
                self.assertEqual(caught.exception.code, expected)
                self.assertNotIn('access-sentinel', str(caught.exception))
                self.assertEqual(len(self.requests), before + 1)
