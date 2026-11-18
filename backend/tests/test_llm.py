"""Bounded retries and safe provider failures, without outgoing requests."""

from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, call, patch

from google.genai import errors
import httpx

from src.config import settings
from src.errors import LLMServiceError
from src.llm import invoke_llm


def provider_error(code):
    error_type = errors.ServerError if code >= 500 else errors.ClientError
    return error_type(code, {"error": {"code": code, "message": "private-provider-text /secret/file test-api-secret"}})


class LLMTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch.object(settings, "gemini_api_key", "test-api-secret"))
        self.factory = self.enterContext(patch("src.llm.genai.Client"))
        self.client = MagicMock()
        self.factory.return_value.__enter__.return_value = self.client
        self.sleep = self.enterContext(patch("src.llm.time.sleep"))

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
