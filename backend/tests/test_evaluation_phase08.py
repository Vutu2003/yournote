"""Check benchmark call accounting and blinded metrics without network usage."""

from contextlib import contextmanager
import json
import unittest
from unittest.mock import patch

import httpx
from pydantic import SecretStr

from evaluation.phase08.benchmark import one_answer
from evaluation.phase08.review import agreement, make_packet, summarize_review
from src.schemas import ChunkMetadata, Citation, RetrievedChunk


class LocalConnection:
    @contextmanager
    def bind_task(self, connection_id, cancellation):
        yield lambda _: SecretStr("synthetic-test-credential")


class TestBenchmarkCalls(unittest.TestCase):
    def run_case(self, operation, *, empty_context=False, raw_text="Câu trả lời [S1]."):
        version = "a" * 64
        locator = {"kind": "paragraph", "anchor": "b000001", "paragraph": 1}
        citation = Citation(source_index=1, source_marker="S1", filename="fixture.txt",
                            document_version=version, locator=locator, source_text="Bằng chứng.")
        chunk = RetrievedChunk(
            text=citation.source_text, score=1,
            metadata=ChunkMetadata(document_id="fixture", filename=citation.filename, source="fixture",
                                   chunk_id="fixture:0:0", document_version=version, locator=locator),
        )
        mapping = {"source": {"filename": citation.filename, "document_version": version}}
        case = {"question": "Câu hỏi?", "sources": ["source"], "pages": []}
        plan = {"k": 5, "model_requested": "test-model", "generation_parameters": {}}
        row = {"retriever": "hybrid"}
        events = []

        def transport(request):
            events.append(("transport", row["model_calls"]))
            if operation == "timeout":
                raise httpx.ReadTimeout("test timeout", request=request)
            if operation == "quota":
                return httpx.Response(429, json={"error": {"code": "subscription_sharing_usage_limit_exceeded"}})
            message = {
                "type": "response.completed",
                "response": {"status": "completed", "model": "test-model-revision",
                             "usage": {"input_tokens": 30, "output_tokens": 10, "total_tokens": 40},
                             "output": [{"content": [{"type": "output_text", "text": raw_text}]}]},
            }
            return httpx.Response(200, text="data: " + json.dumps(message) + "\n\n")

        context = {"history": [], "context": [] if empty_context else [citation.model_dump()]}
        with (
            patch("evaluation.phase08.benchmark.checked_context", return_value=([] if empty_context else [chunk], context)),
            patch("src.providers.chatgpt.new_client", side_effect=lambda: httpx.Client(
                transport=httpx.MockTransport(transport))),
            patch("src.rag.format_citations", return_value=[citation]),
            patch("src.grounding.verify_citation", return_value=object()),
        ):
            one_answer(LocalConnection(), "test", plan, row, case, mapping,
                       lambda: events.append(("checkpoint", row["model_calls"])))
        return row, events

    def test_completion_and_usage(self):
        row, events = self.run_case("ok")
        self.assertEqual(row["status"], "completed")
        self.assertEqual(row["actual_model"], "test-model-revision")
        self.assertEqual(row["usage"]["total_tokens"], 40)
        self.assertEqual(row["valid_citations"], 1)
        self.assertLess(events.index(("checkpoint", 1)), events.index(("transport", 1)))

    def test_quota_and_timeout_already_sent_count_once(self):
        for failure, code in (("quota", "quota_exceeded"), ("timeout", "timeout")):
            with self.subTest(code=code):
                row, events = self.run_case(failure)
                self.assertEqual(row["status"], "error")
                self.assertEqual(row["error_code"], code)
                self.assertEqual(row["model_calls"], 1)
                self.assertEqual(events.count(("transport", 1)), 1)
                self.assertIsNone(row["usage"])

    def test_invalid_marker_retains_raw_answer_and_usage(self):
        row, _ = self.run_case("ok", raw_text="Câu trả lời [S3].")
        self.assertEqual(row["error_code"], "invalid_answer_marker")
        self.assertEqual(row["model_calls"], 1)
        self.assertEqual(row["answer"], "Câu trả lời [S3].")
        self.assertEqual(row["usage"]["total_tokens"], 40)

    def test_empty_context_refusal_never_sends(self):
        row, events = self.run_case("ok", empty_context=True)
        self.assertEqual(row["status"], "completed")
        self.assertEqual(row["model_calls"], 0)
        self.assertFalse(any(event[0] == "transport" for event in events))


class TestBlindedReview(unittest.TestCase):
    def test_blinded_packet_does_not_expose_config_and_empty_human_scores_are_unknown(self):
        rows = [
            {"case_id": "q1", "status": "completed", "split": "main", "retriever": "hybrid",
             "response_seconds": 1, "citations": [], "answer": "Thiếu dữ kiện.", "retrieval": {"context": []}},
            {"case_id": "q2", "status": "not_run", "split": "main", "retriever": "hybrid"},
        ]
        fixture = {"cases": [{"id": "q1", "question": "Câu hỏi?", "referent": None, "history": [],
                              "required_claims": [], "expected_evidence": [], "missing": ["A"], "expected_behavior": "Refuse"}],
                   "pilot_cases": []}
        packet, key, template = make_packet({"plan_sha256": "a" * 64, "rows": rows}, fixture)
        self.assertEqual(len(packet), 1)
        self.assertNotIn("retriever", packet[0])
        self.assertNotIn("case_id", packet[0])
        summary = summarize_review(rows, {}, key)
        self.assertEqual(summary["review_pending"], 1)
        self.assertEqual(summary["not_run"], 1)
        self.assertIsNone(summary["strict_pass_rate"])
        self.assertIsNone(summary["citation_recall"]["rate"])
        self.assertIsNone(template[packet[0]["blind_id"]]["strict_pass"])

    def test_agreement_excludes_pilot_and_accounts_for_marginal_labels(self):
        key = {name: {"split": "pilot" if name == "pilot" else "main"} for name in ("a", "b", "c", "d", "pilot")}
        first = {name: {"strict_pass": name in ("a", "b", "pilot")} for name in key}
        second = {name: {"strict_pass": name in ("a", "c")} for name in key}
        result = agreement(first, second, key)
        self.assertEqual(result["agreement"]["denominator"], 4)
        self.assertEqual(result["agreement"]["rate"], .5)
        self.assertEqual(result["cohens_kappa"], 0)
        self.assertIsNone(agreement({}, {}, key)["cohens_kappa"])
