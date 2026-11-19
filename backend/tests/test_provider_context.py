"""Provider isolation and existing workflows, with no external inference or live data."""

import asyncio
from dataclasses import FrozenInstanceError, asdict
import json
from pathlib import Path
import subprocess
import sys
from threading import Barrier
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from pydantic import SecretStr, ValidationError
from starlette.concurrency import run_in_threadpool

from src.config import Settings, settings
from src.errors import LLMErrorCode, LLMServiceError
from src.llm import (
    current_context, gemini_api_key_scope, generate_llm, invoke_llm, llm_task,
)
from src.providers.contracts import (
    CancellationToken, CredentialRef, ExecutionContext, GenerationParameters,
    LLMRequest, LLMResult, ModelSelection, ProviderCapabilities,
)


def context(model="test-model", reference="connection-test"):
    return ExecutionContext(ModelSelection("gemini", model), CredentialRef(reference))


def resolver(reference):
    return SecretStr("sentinel-runtime-secret") if reference.id == "connection-test" else None


class RecordingProvider:
    capabilities = ProviderCapabilities(supported_parameters=frozenset({"temperature", "max_output_tokens"}))

    def __init__(self, output="answer [S1]"):
        self.output = output
        self.calls = []

    def generate(self, request, execution, *, credential, cancellation):
        self.calls.append((execution, request.parameters, credential.get_secret_value()))
        output = self.output() if callable(self.output) else self.output
        return LLMResult(text=output, provider=execution.selection.provider)


class ProviderContextTests(unittest.TestCase):
    def setUp(self):
        self.provider = RecordingProvider()
        self.enterContext(patch("src.llm.get_provider", return_value=self.provider))

    def test_nested_scopes_restore_context_on_error(self):
        outer, inner = context("outer"), context("inner", "another-connection")
        with llm_task(outer, credential_resolver=resolver):
            self.assertEqual(invoke_llm("test"), "answer [S1]")
            with self.assertRaises(LLMServiceError):
                with llm_task(inner, credential_resolver=lambda ref: None):
                    invoke_llm("test")
            self.assertIs(current_context(), outer)
            invoke_llm("test")
        self.assertIsNone(current_context())
        self.assertEqual([call[0] for call in self.provider.calls], [outer, outer])

    def test_explicit_new_reference_does_not_fall_back_to_environment(self):
        with patch.object(settings, "gemini_api_key", "environment-sentinel"):
            with llm_task(context("new", "missing-connection")):
                with self.assertRaises(LLMServiceError) as caught:
                    invoke_llm("test")
        self.assertEqual(caught.exception.code, LLMErrorCode.RECONNECT_REQUIRED)
        self.assertEqual(self.provider.calls, [])
        self.assertIsNone(current_context())

    def test_exception_in_resolver_is_safe_and_resets_scope(self):
        def broken(reference):
            raise RuntimeError("sentinel-runtime-secret")

        with self.assertRaises(LLMServiceError) as caught:
            with llm_task(context(), credential_resolver=broken):
                invoke_llm("test")
        self.assertEqual(caught.exception.code, LLMErrorCode.RECONNECT_REQUIRED)
        self.assertNotIn("sentinel-runtime-secret", str(caught.exception))
        self.assertIsNone(current_context())

    def test_generation_failure_resets_scope_and_hides_arbitrary_provider_message(self):
        with patch.object(self.provider, "generate", side_effect=RuntimeError("sentinel-runtime-secret")):
            with self.assertRaises(LLMServiceError) as caught:
                with llm_task(context(), credential_resolver=resolver):
                    invoke_llm("test")
        self.assertEqual(caught.exception.code, LLMErrorCode.REQUEST_REJECTED)
        self.assertNotIn("sentinel-runtime-secret", str(caught.exception))
        self.assertIsNone(current_context())

    def test_snapshot_is_frozen_and_does_not_reread_config_mid_task(self):
        with patch.object(settings, "llm_model", "first-model"), patch.object(settings, "gemini_api_key", "first-key"):
            with llm_task() as execution:
                invoke_llm("first")
                with patch.object(settings, "llm_model", "second-model"), patch.object(settings, "gemini_api_key", "second-key"):
                    invoke_llm("second")
                with self.assertRaises(FrozenInstanceError):
                    execution.selection.model = "changed"
        self.assertEqual([call[0].selection.model for call in self.provider.calls], ["first-model", "first-model"])
        self.assertEqual([call[2] for call in self.provider.calls], ["first-key", "first-key"])
        self.assertEqual(len({call[0].request_id for call in self.provider.calls}), 1)

    def test_capability_rejection_precedes_invocation(self):
        self.provider.capabilities = ProviderCapabilities()
        with llm_task(context(), credential_resolver=resolver):
            with self.assertRaises(LLMServiceError) as caught:
                generate_llm(LLMRequest("test", GenerationParameters(temperature=0.1)))
        self.assertEqual(caught.exception.code, LLMErrorCode.UNSUPPORTED_CAPABILITY)
        self.assertEqual(self.provider.calls, [])

    def test_cancel_before_and_after_provider_prevents_success(self):
        for when in ("before", "after"):
            with self.subTest(when=when):
                cancellation = CancellationToken()
                if when == "before":
                    cancellation.cancel()
                else:
                    self.provider.output = lambda: (cancellation.cancel() or "answer")
                with self.assertRaises(LLMServiceError) as caught:
                    with llm_task(context(), credential_resolver=resolver, cancellation=cancellation):
                        invoke_llm("test")
                self.assertEqual(caught.exception.code, LLMErrorCode.CANCELLED)
                self.assertIsNone(current_context())
        self.assertEqual(len(self.provider.calls), 1)

    def test_nested_cancel_override_preserves_connection(self):
        with llm_task(context(), credential_resolver=resolver):
            with llm_task(cancellation=CancellationToken()):
                invoke_llm("test")
        self.assertEqual(self.provider.calls[0][2], "sentinel-runtime-secret")

    def test_legacy_key_override_and_failure_restore_environment(self):
        with patch.object(settings, "gemini_api_key", "environment-key"):
            with self.assertRaises(ValueError):
                with gemini_api_key_scope("  legacy-key  "):
                    invoke_llm("test")
                    raise ValueError("application error")
            self.assertIsNone(current_context())
            invoke_llm("test")
            with gemini_api_key_scope(""):
                invoke_llm("test")
        self.assertEqual([call[2] for call in self.provider.calls], ["legacy-key", "environment-key", "environment-key"])

    def test_context_and_result_serialization_exclude_credential(self):
        with llm_task(context(), credential_resolver=resolver) as execution:
            result = generate_llm(LLMRequest("test"))
        safe = json.dumps({"context": asdict(execution), "result": asdict(result)}, default=str)
        self.assertNotIn("sentinel-runtime-secret", safe)
        with patch.object(settings, "gemini_api_key", "sentinel-runtime-secret"):
            self.assertNotIn("sentinel-runtime-secret", repr(settings))
            self.assertNotIn("sentinel-runtime-secret", settings.model_dump_json())

    def test_async_tasks_and_fastapi_threadpool_keep_separate_credentials(self):
        barrier = Barrier(2, timeout=5)
        recorded = []

        def generate(request, execution, *, credential, cancellation):
            barrier.wait()
            self.assertIs(current_context(), execution)
            recorded.append((execution.selection.model, credential.get_secret_value(), execution.request_id))
            return LLMResult(text=execution.selection.model, provider="gemini")

        async def task(index):
            execution = context(f"model-{index}", f"connection-{index}")
            with llm_task(execution, credential_resolver=lambda ref: SecretStr(f"key-{index}")):
                value = await run_in_threadpool(invoke_llm, "test")
                self.assertIs(current_context(), execution)
            self.assertIsNone(current_context())
            return value

        async def run():
            return await asyncio.wait_for(asyncio.gather(task(1), task(2)), timeout=10)

        with patch.object(self.provider, "generate", side_effect=generate):
            self.assertEqual(asyncio.run(run()), ["model-1", "model-2"])
        self.assertEqual({(model, key) for model, key, _ in recorded}, {("model-1", "key-1"), ("model-2", "key-2")})
        self.assertEqual(len({request_id for _, _, request_id in recorded}), 2)
        self.assertIsNone(current_context())


class ProviderValidationTests(unittest.TestCase):
    def test_unknown_provider_or_bad_model_is_rejected_without_sdk_call(self):
        with patch("src.providers.gemini.genai.Client") as sdk:
            for provider, model, expected in [
                ("unknown", "model", LLMErrorCode.UNSUPPORTED_PROVIDER),
                ("gemini", "", LLMErrorCode.MODEL_UNAVAILABLE),
                ("gemini", "model\nprivate", LLMErrorCode.MODEL_UNAVAILABLE),
            ]:
                with self.subTest(provider=provider, model=model), self.assertRaises(LLMServiceError) as caught:
                    with llm_task(ExecutionContext(ModelSelection(provider, model))):
                        invoke_llm("test")
                self.assertEqual(caught.exception.code, expected)
            sdk.assert_not_called()
        with self.assertRaises(ValidationError):
            Settings(_env_file=None, llm_model=" ")

    def test_health_and_openapi_do_not_import_sdk_embedding_or_rag(self):
        script = '''
import importlib.abc
import sys
class RejectHeavyImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        forbidden = ("google.genai", "sentence_transformers", "src.embeddings", "src.store", "src.rag", "src.learning", "src.mindmap")
        if any(fullname == name or fullname.startswith(name + ".") for name in forbidden):
            raise AssertionError("Unexpected startup import: " + fullname)
sys.meta_path.insert(0, RejectHeavyImports())
from backend.main import app, health
assert health().status == "ok"
assert "/api/chat" in app.app.openapi()["paths"]
print("lazy startup passed")
'''
        completed = subprocess.run(
            [sys.executable, "-c", script], cwd=Path(__file__).resolve().parents[2],
            capture_output=True, text=True, timeout=20,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("lazy startup passed", completed.stdout)


class ExistingWorkflowProviderTests(unittest.TestCase):
    def setUp(self):
        from src.schemas import ChunkMetadata, RetrievedChunk

        self.chunks = [RetrievedChunk(text=f"Course material {i}", score=0, metadata=ChunkMetadata(
            filename="course.pdf", document_id="course", source="/private/course.pdf", page=i, chunk_id=f"course:{i}:0",
        )) for i in (1, 2)]
        self.provider = RecordingProvider()
        self.enterContext(patch("src.llm.get_provider", return_value=self.provider))
        for name in ("src.rag.retrieve", "src.rag.fetch_all_chunks", "src.learning.retrieve", "src.learning.fetch_all_chunks"):
            self.enterContext(patch(name, return_value=self.chunks))
        self.enterContext(patch("src.store.list_documents", return_value=[{"filename": "course.pdf", "pages": [1, 2]}]))

    def test_chat_reading_and_all_studio_tools_use_shared_provider(self):
        from backend.schemas.api import ChatRequest, SummaryRequest, QuizRequest, FlashcardsRequest, MindMapRequest
        from backend.schemas.reading import ReadingChatRequest, ReadingDocument
        from backend.services import core_adapter, reading

        summary = json.dumps({"summary": "Course summary [S1]", "key_points": ["Point"]})
        quiz = json.dumps({"items": [{"question": "Which?", "options": ["A", "B", "C", "D"],
                                       "correct_index": 0, "explanation": "Because [S1]", "source_markers": ["S1"]}]})
        cards = json.dumps({"cards": [{"front": "Concept", "back": "Explanation", "source_markers": ["S1"]}]})
        tree = json.dumps({"root": {"label": "Course", "children": [{"label": "Concept", "source_markers": ["S1"]}]}})
        operations = [
            (lambda: core_adapter.chat(ChatRequest(question="Explain", filenames=["course.pdf"])), "Answer [S1]"),
            (lambda: core_adapter.summary(SummaryRequest(filenames=["course.pdf"])), summary),
            (lambda: core_adapter.quiz(QuizRequest(filenames=["course.pdf"])), quiz),
            (lambda: core_adapter.flashcards(FlashcardsRequest(filenames=["course.pdf"])), cards),
            (lambda: core_adapter.mindmap(MindMapRequest(filenames=["course.pdf"])), tree),
        ]
        for operation, output in operations:
            self.provider.output = output
            with llm_task(context(), credential_resolver=resolver):
                result = operation()
            self.assertNotIn("sentinel-runtime-secret", result.model_dump_json())
            self.assertNotIn("sentinel-runtime-secret", core_adapter.markdown(SimpleNamespace(
                feature=("chat" if hasattr(result, "answer") else "summary" if hasattr(result, "summary") else
                         "quiz" if hasattr(result, "items") else "flashcards" if hasattr(result, "cards") else "mindmap"),
                result=result,
            )))
            self.assertIsNone(current_context())
        self.provider.output = "Reading answer [S1]"
        info = ReadingDocument(document_id="course", filename="course.pdf", document_version="a" * 64, page_count=2)
        with patch.object(reading, "document", return_value=(info, Path("unused.pdf"))), patch.object(
            reading.notebooks, "get_notebook", return_value=SimpleNamespace(state=SimpleNamespace(document_filenames=["course.pdf"])),
        ), llm_task(context(), credential_resolver=resolver):
            result = reading.chat("notebook-id", ReadingChatRequest(document_id="course", question="Explain"))
        self.assertEqual(result.answer, "Reading answer [S1]")
        self.assertEqual(len(self.provider.calls), 6)
        self.assertTrue(all(call[0].selection.model == "test-model" for call in self.provider.calls))

    def test_summary_and_mindmap_map_reduce_share_one_request_snapshot(self):
        from src.learning import summarize
        from src.mindmap import generate_mindmap

        outputs = iter(json.dumps({"summary": f"Summary [{marker}]", "key_points": []}) for marker in ('S1','S2','S1'))
        self.provider.output = lambda: next(outputs)
        with patch.object(settings, "summarize_batch_size", 1), llm_task(context(), credential_resolver=resolver):
            summarize(filters={"filename": "course.pdf"})
        self.assertEqual(len(self.provider.calls), 3)
        self.assertEqual(len({call[0].request_id for call in self.provider.calls}), 1)
        self.provider.calls.clear()
        outputs = iter(json.dumps({"root": {"label": "Course", "children": [
            {"label": "Concept", "source_markers": markers},
        ]}}) for markers in (["S1"], ["S2"], ["S1", "S2"]))
        self.provider.output = lambda: next(outputs)
        with patch.object(settings, "mindmap_batch_size", 1), llm_task(context(), credential_resolver=resolver):
            generate_mindmap(filters={"filename": "course.pdf"})
        self.assertEqual(len(self.provider.calls), 3)
        self.assertEqual(len({call[0].request_id for call in self.provider.calls}), 1)
        self.assertTrue(all(call[2] == "sentinel-runtime-secret" for call in self.provider.calls))
        self.assertIsNone(current_context())

    def test_standalone_summary_creates_snapshot_for_all_batches(self):
        from src.learning import summarize

        def output():
            # Simulate external settings changing while an operation is active.
            settings.llm_model = "later-model"
            settings.gemini_api_key = "later-key"
            return json.dumps({"summary": "Summary [S2]" if len(self.provider.calls)==2 else "Summary [S1]", "key_points": []})

        self.provider.output = output
        with patch.object(settings, "llm_model", "initial-model"), patch.object(
            settings, "gemini_api_key", "initial-key",
        ), patch.object(settings, "summarize_batch_size", 1):
            summarize(filters={"filename": "course.pdf"})
        self.assertEqual(len(self.provider.calls), 3)
        self.assertEqual(len({call[0].request_id for call in self.provider.calls}), 1)
        self.assertTrue(all(call[0].selection.model == "initial-model" for call in self.provider.calls))
        self.assertTrue(all(call[2] == "initial-key" for call in self.provider.calls))
        self.assertIsNone(current_context())
