"""Run: .venv/bin/python -m unittest discover -s backend/tests -v.

Only upload delegation/failure is substituted: the real baseline must not
be written to. Documents, selection checks and exports use real core code.
No generation requests with valid, indexed selections are made here.
"""

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.main import app
from backend.schemas.api import ChatRequest
from backend.services import core_adapter


class APIContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.context = TestClient(app, raise_server_exceptions=False)
        cls.client = cls.context.__enter__()
        response = cls.client.get("/api/documents")
        assert response.status_code == 200, response.text
        cls.documents = response.json()["documents"]
        cls.filename = cls.documents[0]["filename"]

    @classmethod
    def tearDownClass(cls):
        cls.context.__exit__(None, None, None)

    def test_health(self):
        self.assertEqual(self.client.get("/api/health").json(), {"status": "ok"})

    def test_real_documents(self):
        self.assertGreaterEqual(len(self.documents), 1)
        for item in self.documents:
            self.assertEqual(set(item), {"filename", "document_id", "pages", "page_count", "chunk_count"})
            self.assertEqual(item["page_count"], len(item["pages"]))
            self.assertGreater(item["chunk_count"], 0)
            self.assertNotIn("/", item["filename"])

    def test_upload_validation(self):
        cases = [
            ("bad.txt", b"text", "text/plain"),
            ("empty.pdf", b"", "application/pdf"),
            ("corrupt.pdf", b"non-pdf", "application/pdf"),
            ("../bad.pdf", b"%PDF-1.4", "application/pdf"),
            ("folder\\bad.pdf", b"%PDF-1.4", "application/pdf"),
            ("bad.pdf", b"%PDF-1.4", "image/png"),
        ]
        for filename, data, content_type in cases:
            with self.subTest(filename=filename):
                response = self.client.post("/api/documents/upload", files={"file": (filename, data, content_type)})
                self.assertEqual(response.status_code, 400)
        self.assertEqual(self.client.post("/api/documents/upload").status_code, 422)

    def test_upload_size_guard(self):
        with patch("backend.api.routes.documents.MAX_UPLOAD_BYTES", 8):
            response = self.client.post("/api/documents/upload", files={"file": ("large.pdf", b"%PDF-1.4-too-long", "application/pdf")})
        self.assertEqual(response.status_code, 400)

    def test_upload_delegates_to_core_without_baseline_write(self):
        with patch("src.indexing.save_and_ingest_pdf", return_value={"filename": "isolated.pdf", "chunks_indexed": 2}) as ingest:
            response = self.client.post("/api/documents/upload", files={"file": ("isolated.pdf", b"%PDF-1.4", "application/pdf")})
        ingest.assert_called_once_with(b"%PDF-1.4", "isolated.pdf")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"filename": "isolated.pdf", "chunks_indexed": 2})

    def test_core_failure_is_safe_and_logs_redact_key(self):
        from src.config import settings

        key = settings.gemini_api_key or "test-secret"
        with patch("src.indexing.save_and_ingest_pdf", side_effect=RuntimeError(f"private /home/internal/data/secret.pdf {key}")), patch("backend.main.logger.error") as log:
            response = self.client.post("/api/documents/upload", headers={"Origin": "http://localhost:5173"}, files={"file": ("isolated.pdf", b"%PDF-1.4", "application/pdf")})
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.headers.get("access-control-allow-origin"), "http://localhost:5173")
        self.assertEqual(response.json(), {"detail": "Unable to complete the operation. Please try again."})
        self.assertNotIn(key, response.text)
        if settings.gemini_api_key:
            self.assertNotIn(key, str(log.call_args))
        log.assert_called_once()

    def test_chat_validation(self):
        base = {"question": "Grounded question", "filenames": [self.filename]}
        cases = [
            {}, {**base, "question": "   "}, {**base, "filenames": []},
            {**base, "filenames": "not-a-list"}, {**base, "filenames": ["../x.pdf"]},
            {**base, "pages": [0]}, {**base, "pages": [1, 2]},
            {**base, "pages": [1], "filenames": [d["filename"] for d in self.documents]},
            {**base, "k": 0}, {**base, "k": 65}, {**base, "k": True},
            {**base, "api_key": "SENTINEL_PRIVATE_VALUE"},
        ]
        for body in cases:
            with self.subTest(body=body):
                response = self.client.post("/api/chat", json=body)
                self.assertEqual(response.status_code, 422)
                self.assertNotIn("SENTINEL_PRIVATE_VALUE", response.text)
                for issue in response.json()["detail"]:
                    self.assertEqual(set(issue), {"loc", "msg", "type"})

    def test_ai_failure_returns_safe_status_and_cors_instead_of_network_error(self):
        from src.errors import LLMServiceError

        for origin in ("http://localhost:5173", "http://127.0.0.1:5173", "https://untrusted.example"):
            for status, detail in [(503, "AI service is temporarily unavailable."), (429, "AI service rate limit exceeded."), (504, "AI service timed out.")]:
                with self.subTest(origin=origin, status=status), patch("backend.services.core_adapter.mindmap", side_effect=LLMServiceError(status, detail)):
                    response = self.client.post("/api/mindmap", headers={"Origin": origin}, json={"filenames": [self.filename]})
                self.assertEqual(response.status_code, status)
                self.assertEqual(response.json(), {"detail": detail})
                if origin == "https://untrusted.example":
                    self.assertNotIn("access-control-allow-origin", response.headers)
                else:
                    self.assertEqual(response.headers.get("access-control-allow-origin"), origin)
                if status in (503, 504):
                    self.assertEqual(response.headers.get("Retry-After"), "5")

        with patch("src.indexing.save_and_ingest_pdf", side_effect=RuntimeError("private")), patch("backend.main.logger.error"):
            response = self.client.post("/api/documents/upload", headers={"Origin": "https://untrusted.example"}, files={"file": ("isolated.pdf", b"%PDF-1.4", "application/pdf")})
        self.assertEqual(response.status_code, 500)
        self.assertNotIn("access-control-allow-origin", response.headers)

    def test_learning_validation(self):
        for route, max_count in [("summary", None), ("quiz", 50), ("flashcards", 100), ("mindmap", None)]:
            cases = [{}, {"filenames": []}, {"filenames": [self.filename], "pages": [-1]},
                     {"filenames": [self.filename], "k": 129}]
            if max_count:
                cases.extend({"filenames": [self.filename], "count": count} for count in [0, max_count + 1, True])
            for body in cases:
                with self.subTest(route=route, body=body):
                    self.assertEqual(self.client.post(f"/api/{route}", json=body).status_code, 422)

    def test_unknown_document_and_page(self):
        for route in ["chat", "summary", "quiz", "flashcards", "mindmap"]:
            body = {"filenames": ["not-indexed.pdf"]}
            if route == "chat":
                body["question"] = "A question"
            with self.subTest(route=route):
                self.assertEqual(self.client.post(f"/api/{route}", json=body).status_code, 404)
        response = self.client.post("/api/chat", json={"question": "A question", "filenames": [self.filename], "pages": [99999]})
        self.assertEqual(response.status_code, 404)

    def test_supported_filters_use_core_normalization(self):
        with core_adapter._core_lock:
            filters = core_adapter._filters(ChatRequest(question="q", filenames=[self.filename], pages=[self.documents[0]["pages"][0]]))
            multiple = core_adapter._filters(ChatRequest(question="q", filenames=[d["filename"] for d in self.documents]))
        self.assertEqual(filters, {"filename": self.filename, "page": self.documents[0]["pages"][0]})
        if len(self.documents) > 1:
            self.assertEqual(multiple, {"filenames": [d["filename"] for d in self.documents]})

    def test_cors(self):
        for origin in ["http://localhost:5173", "http://127.0.0.1:5173"]:
            response = self.client.options("/api/chat", headers={"Origin": origin, "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "Content-Type"})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers["access-control-allow-origin"], origin)
            self.assertNotIn("access-control-allow-credentials", response.headers)
            self.assertIn("POST", response.headers["access-control-allow-methods"])
        response = self.client.options("/api/chat", headers={"Origin": "https://untrusted.example", "Access-Control-Request-Method": "POST"})
        self.assertEqual(response.status_code, 400)
        self.assertNotIn("access-control-allow-origin", response.headers)
        response = self.client.get("/api/documents", headers={"Origin": "http://localhost:5173"})
        self.assertIn("Content-Disposition", response.headers["access-control-expose-headers"])

    def test_export_uses_renderer_without_paths(self):
        response = self.client.post("/api/export", json={"feature": "summary", "result": {"scope": "filter", "summary": "Known text", "key_points": ["Known point"], "citations": []}})
        self.assertEqual(response.status_code, 200)
        self.assertIn("Known text", response.text)
        self.assertTrue(response.headers["content-type"].startswith("text/markdown"))
        self.assertEqual(response.headers["content-disposition"], 'attachment; filename="summary.md"')
        rejected = self.client.post("/api/export", json={"feature": "summary", "result": {"scope": "filter", "summary": "text"}, "output": "/tmp/not-allowed.md"})
        self.assertEqual(rejected.status_code, 422)
        mismatched = self.client.post("/api/export", json={"feature": "quiz", "result": {"scope": "filter", "items": [{"question": "q", "options": ["one"], "correct_index": 4, "explanation": "e"}]}})
        self.assertEqual(mismatched.status_code, 422)

    def test_openapi_and_docs(self):
        schema = self.client.get("/openapi.json").json()
        self.assertEqual(len(schema["paths"]), 17)
        for path, operation in schema["paths"].items():
            for method, details in operation.items():
                self.assertTrue(details["summary"])
                success = "204" if method == "delete" else "201" if method == "post" and (path == "/api/notebooks" or path.endswith("/highlights")) else "200"
                self.assertIn(success, details["responses"])
                if method in {"post", "put"}:
                    self.assertIn("requestBody", details)
                    self.assertIn("422", details["responses"])
        self.assertIn("text/markdown", schema["paths"]["/api/export"]["post"]["responses"]["200"]["content"])
        self.assertEqual(self.client.get("/docs").status_code, 200)


if __name__ == "__main__":
    unittest.main()
