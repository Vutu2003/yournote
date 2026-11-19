"""Bounded retries and safe provider failures, without outgoing requests."""

from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, call, patch

from google.genai import errors
import httpx

from src.config import settings
from src.errors import LLMErrorCode, LLMServiceError
from src.llm import generate_llm, invoke_llm, llm_task
from src.providers.contracts import CancellationToken, LLMRequest


def provider_error(code):
    error_type = errors.ServerError if code >= 500 else errors.ClientError
    return error_type(code, {"error": {"code": code, "message": "private-provider-text /secret/file test-api-secret"}})


class LLMTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch.object(settings, "gemini_api_key", "test-api-secret"))
        self.factory = self.enterContext(patch("src.providers.gemini.genai.Client"))
        self.client = MagicMock()
        self.factory.return_value.__enter__.return_value = self.client
        self.sleep = self.enterContext(patch("src.providers.contracts.CancellationToken.wait", return_value=False))

    def test_transient_failure_recovers_and_closes_connections(self):
        self.client.models.generate_content.side_effect = [provider_error(503), SimpleNamespace(text=" answer ")]
        self.assertEqual(invoke_llm("test"), "answer")
        self.assertEqual(self.client.models.generate_content.call_count, 2)
        self.sleep.assert_called_once_with(1)
        options = self.factory.call_args.kwargs["http_options"]
        self.assertEqual(options.timeout, 60000)
        self.assertEqual(options.retry_options.attempts, 1)
        self.factory.return_value.__exit__.assert_called_once()

    def test_repeated_overload_is_bounded_and_safe(self):
        self.client.models.generate_content.side_effect = provider_error(503)
        with self.assertRaises(LLMServiceError) as caught:
            invoke_llm("test")
        self.assertEqual(caught.exception.status_code, 503)
        self.assertEqual(caught.exception.detail, "AI service is temporarily unavailable.")
        self.assertNotIn("test-api-secret", str(caught.exception))
        self.assertEqual(self.client.models.generate_content.call_count, 3)
        self.assertEqual(self.sleep.call_args_list, [call(1), call(2)])
        self.factory.return_value.__exit__.assert_called_once()

    def test_quota_and_configuration_errors_are_not_retried(self):
        for code, status in [(429, 429), (401, 502), (403, 502), (404, 502), (400, 502)]:
            with self.subTest(code=code):
                self.client.models.generate_content.reset_mock()
                self.client.models.generate_content.side_effect = provider_error(code)
                with self.assertRaises(LLMServiceError) as caught:
                    invoke_llm("test")
                self.assertEqual(caught.exception.status_code, status)
                self.assertNotIn("private-provider-text", caught.exception.detail)
                self.assertEqual(self.client.models.generate_content.call_count, 1)
                self.sleep.assert_not_called()

    def test_transport_timeout_and_connection_failures_are_reported(self):
        for failure, status in [(httpx.ReadTimeout("private"), 504), (httpx.ConnectError("private"), 503)]:
            with self.subTest(status=status):
                self.client.models.generate_content.reset_mock()
                self.client.models.generate_content.side_effect = failure
                with self.assertRaises(LLMServiceError) as caught:
                    invoke_llm("test")
                self.assertEqual(caught.exception.status_code, status)
                self.assertEqual(self.client.models.generate_content.call_count, 3)
                self.assertNotIn("private", caught.exception.detail)

    def test_missing_key_and_empty_output_have_safe_errors(self):
        with patch.object(settings, "gemini_api_key", None):
            with self.assertRaises(LLMServiceError) as caught:
                invoke_llm("test")
            self.assertEqual(caught.exception.detail, "AI service is not configured.")
        self.factory.assert_not_called()
        self.client.models.generate_content.return_value = SimpleNamespace(text="")
        with self.assertRaises(LLMServiceError) as caught:
            invoke_llm("test")
        self.assertEqual(caught.exception.status_code, 502)
        self.sleep.assert_not_called()

    def test_result_only_reports_metadata_received_from_provider(self):
        self.client.models.generate_content.return_value = SimpleNamespace(
            text=" answer ", model_version="gemini-actual-version",
            usage_metadata=SimpleNamespace(prompt_token_count=0, candidates_token_count=4, total_token_count=7),
        )
        result = generate_llm(LLMRequest("test"))
        self.assertEqual(result.text, "answer")
        self.assertEqual(result.provider, "gemini")
        self.assertEqual(result.model, "gemini-actual-version")
        self.assertEqual((result.usage.input_tokens, result.usage.output_tokens, result.usage.total_tokens), (0, 4, 7))
        self.assertGreaterEqual(result.duration_seconds, 0)
        self.client.models.generate_content.return_value = SimpleNamespace(text="answer")
        unknown = generate_llm(LLMRequest("test"))
        self.assertIsNone(unknown.model)
        self.assertIsNone(unknown.usage)

    def test_partial_usage_is_not_inferred(self):
        self.client.models.generate_content.return_value = SimpleNamespace(
            text="answer", usage_metadata=SimpleNamespace(prompt_token_count=5, total_token_count=12),
        )
        result = generate_llm(LLMRequest("test"))
        self.assertEqual(result.usage.input_tokens, 5)
        self.assertIsNone(result.usage.output_tokens)
        self.assertEqual(result.usage.total_tokens, 12)

    def test_error_codes_preserve_existing_http_messages(self):
        for status, code in [(401, LLMErrorCode.RECONNECT_REQUIRED), (404, LLMErrorCode.MODEL_UNAVAILABLE),
                             (429, LLMErrorCode.RATE_LIMITED), (503, LLMErrorCode.TEMPORARILY_UNAVAILABLE)]:
            with self.subTest(status=status):
                self.client.models.generate_content.side_effect = provider_error(status)
                with self.assertRaises(LLMServiceError) as caught:
                    invoke_llm("test")
                self.assertEqual(caught.exception.code, code)

    def test_constructor_and_response_errors_do_not_leak_provider_details(self):
        self.factory.side_effect = ValueError("test-api-secret private-provider-text")
        with self.assertRaises(LLMServiceError) as caught:
            invoke_llm("test")
        self.assertEqual(caught.exception.code, LLMErrorCode.REQUEST_REJECTED)
        self.assertNotIn("test-api-secret", str(caught.exception))
        self.assertTrue(caught.exception.__suppress_context__)

    def test_cancel_during_backoff_stops_retries_and_closes_client(self):
        cancellation = CancellationToken()
        self.client.models.generate_content.side_effect = provider_error(503)
        with patch.object(cancellation, "wait", side_effect=lambda seconds: cancellation.cancel()):
            with self.assertRaises(LLMServiceError) as caught:
                with llm_task(cancellation=cancellation):
                    invoke_llm("test")
        self.assertEqual(caught.exception.code, LLMErrorCode.CANCELLED)
        self.assertEqual(self.client.models.generate_content.call_count, 1)
        self.factory.return_value.__exit__.assert_called_once()
