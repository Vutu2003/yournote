"""Exercise original PDF access, annotation isolation and selected-source grounding."""

import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from backend.main import app
from backend.schemas.api import DocumentsResponse
from src.config import settings


def write_pdf(path, text="The study compares two methods and finds lower error."):
    writer = PdfWriter()
    for sentence in [text, "The next page explains the methods and limitations."]:
        page = writer.add_blank_page(width=612, height=792)
        font = DictionaryObject({NameObject("/Type"): NameObject("/Font"), NameObject("/Subtype"): NameObject("/Type1"), NameObject("/BaseFont"): NameObject("/Helvetica")})
        page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})})
        stream = DecodedStreamObject()
        stream.set_data(f"BT /F1 12 Tf 50 700 Td ({sentence}) Tj ET".encode())
        page[NameObject("/Contents")] = writer._add_object(stream)
    writer.write(path)


class ReadingTests(unittest.TestCase):
    def setUp(self):
        self.temporary = self.enterContext(TemporaryDirectory(prefix="reading-test-"))
        root = Path(self.temporary)
        self.data = root / "data"
        self.data.mkdir()
        self.pdf = self.data / "paper.pdf"
        write_pdf(self.pdf)
        self.original = self.pdf.read_bytes()
        self.enterContext(patch.object(settings, "data_dir", self.data))
        self.enterContext(patch("backend.services.notebooks._database_path", return_value=root / "notebooks.sqlite"))
        self.enterContext(patch("src.store.list_documents", return_value=[]))
        self.enterContext(patch("backend.services.core_adapter.documents", return_value=DocumentsResponse(documents=[{
            "filename": "paper.pdf", "document_id": "paper-id", "pages": [1, 2], "page_count": 2, "chunk_count": 2,
        }])))
        self.client = self.enterContext(TestClient(app))
        self.notebook = self.create_notebook()
        self.other = self.create_notebook()
        self.base = f"/api/notebooks/{self.notebook['id']}/documents/paper-id"
        self.info = self.client.get(self.base).json()

    def create_notebook(self):
        notebook = self.client.post("/api/notebooks", json={"title": "PDF test"}).json()
        state = notebook["state"]
        state.update(document_filenames=["paper.pdf"], selected=["paper.pdf"])
        return self.client.put(f"/api/notebooks/{notebook['id']}", json={"title": notebook["title"], "icon": notebook["icon"], "state": state}).json()

    def draft(self, **overrides):
        return {"document_version": self.info["document_version"], "page": 1, "text": "The study compares two methods", "rects": [{"x": .1, "y": .1, "width": .5, "height": .02}], **overrides}

    def test_original_download_and_range_preserve_bytes(self):
        self.assertEqual(self.info["document_version"], hashlib.sha256(self.original).hexdigest())
        self.assertEqual(self.info["page_count"], 2)
        self.assertNotIn("source", self.info)
        response = self.client.get(self.base + "/pdf")
        self.assertEqual(response.content, self.original)
        self.assertIn("inline", response.headers["content-disposition"])
        self.assertIn("attachment", self.client.get(self.base + "/pdf?download=true").headers["content-disposition"])
        response = self.client.get(self.base + "/pdf", headers={"Range": "bytes=0-9"})
        self.assertEqual(response.status_code, 206)
        self.assertEqual(response.content, self.original[:10])
        self.assertEqual(self.client.get(self.base + "/pdf?version=old").status_code, 409)

    def test_reset_clears_only_target_workspace_and_preserves_shared_pdf(self):
        from backend.schemas.notebooks import WorkspaceState

        notebook_path = f"/api/notebooks/{self.notebook['id']}"
        state = self.notebook["state"]
        state.update(source_names={"paper.pdf": "Tên nguồn"}, page="2", active_tool="quiz",
                     chat=[{"question": "Question", "answer": "Answer", "citations": []}])
        for feature, result in [
            ("summary", {"summary": "Saved summary"}),
            ("quiz", {"items": [{"question": "Q", "options": ["A", "B", "C", "D"], "correct_index": 1, "explanation": "Reason"}]}),
            ("flashcard", {"cards": [{"front": "Front", "back": "Back"}]}),
        ]:
            state[f"{feature}_artifacts"] = [{"id": feature, "title": feature, "createdAt": 1,
                "sourceFilenames": ["paper.pdf"], "pages": [2], "topic": None,
                "result": {"scope": "document", **result}}]
        saved = self.client.put(notebook_path, json={"title": "Keep this title", "icon": "🔬", "state": state})
        self.assertEqual(saved.status_code, 200, saved.text)
        self.assertEqual(self.client.post(self.base + "/highlights", json=self.draft()).status_code, 201)
        other_base = self.base.replace(self.notebook["id"], self.other["id"])
        self.assertEqual(self.client.post(other_base + "/highlights", json=self.draft()).status_code, 201)
        other_before = self.client.get(f"/api/notebooks/{self.other['id']}").json()
        highlights_before = self.client.get(other_base + "/highlights").json()

        response = self.client.post(notebook_path + "/reset", json={"confirmation": "ĐẶT LẠI"})
        self.assertEqual(response.status_code, 200, response.text)
        reset = response.json()
        for key in ("id", "title", "icon", "created_at"):
            self.assertEqual(reset[key], saved.json()[key])
        self.assertEqual(reset["state"], WorkspaceState().model_dump(mode="json"))
        self.assertEqual((reset["source_count"], reset["chat_count"]), (0, 0))
        self.assertEqual(self.client.get(notebook_path).json(), reset)
        self.assertEqual(len(self.client.get("/api/notebooks").json()["notebooks"]), 2)
        self.assertEqual(self.client.get(f"/api/notebooks/{self.other['id']}").json(), other_before)
        self.assertEqual(self.client.get(other_base + "/highlights").json(), highlights_before)
        self.assertEqual(self.client.get(other_base + "/pdf?download=true").content, self.original)
        self.assertEqual(self.pdf.read_bytes(), self.original)
        # Reattach the source: prior highlights must stay deleted, and the
        # unchanged shared index/PDF remains available for normal use.
        reset["state"].update(document_filenames=["paper.pdf"], selected=["paper.pdf"])
        self.assertEqual(self.client.put(notebook_path, json={key: reset[key] for key in ("title", "icon", "state")}).status_code, 200)
        self.assertEqual(self.client.get(self.base + "/highlights").json()["highlights"], [])
        self.assertEqual(self.client.get(self.base + "/pdf").content, self.original)

    def test_reset_requires_confirmation_and_existing_notebook(self):
        path = f"/api/notebooks/{self.notebook['id']}"
        before = self.client.get(path).json()
        for body in ({}, {"confirmation": ""}, {"confirmation": "XÓA TẤT CẢ"}):
            self.assertEqual(self.client.post(path + "/reset", json=body).status_code, 422)
        self.assertEqual(self.client.get(path).json(), before)
        self.assertEqual(self.client.post("/api/notebooks/missing/reset", json={"confirmation": "ĐẶT LẠI"}).status_code, 404)

    def test_reset_database_failure_rolls_back_workspace_and_highlights(self):
        from backend.services.notebooks import _database

        self.client.post(self.base + "/highlights", json=self.draft())
        path = f"/api/notebooks/{self.notebook['id']}"
        before = self.client.get(path).json()
        highlights = self.client.get(self.base + "/highlights").json()
        with _database() as connection:
            connection.execute("CREATE TRIGGER refuse_reset BEFORE DELETE ON pdf_highlights BEGIN SELECT RAISE(ABORT, 'test reset failure'); END")
        with TestClient(app, raise_server_exceptions=False) as client, patch("backend.main.logger.error"):
            self.assertEqual(client.post(path + "/reset", json={"confirmation": "ĐẶT LẠI"}).status_code, 500)
        self.assertEqual(self.client.get(path).json(), before)
        self.assertEqual(self.client.get(self.base + "/highlights").json(), highlights)

    def test_membership_and_file_boundaries(self):
        empty = self.client.post("/api/notebooks", json={"title": "Empty"}).json()
        self.assertEqual(self.client.get(f"/api/notebooks/{empty['id']}/documents/paper-id/pdf").status_code, 404)
        self.assertEqual(self.client.get(self.base.replace("paper-id", "unknown") + "/pdf").status_code, 404)
        outside = Path(self.temporary) / "outside.pdf"
        outside.write_bytes(self.original)
        self.pdf.unlink()
        self.pdf.symlink_to(outside)
        self.assertEqual(self.client.get(self.base + "/pdf").status_code, 404)

    def test_highlight_persistence_isolation_delete_and_cascade(self):
        response = self.client.post(self.base + "/highlights", json=self.draft())
        self.assertEqual(response.status_code, 201, response.text)
        highlight = response.json()
        self.assertEqual(self.pdf.read_bytes(), self.original)
        self.assertEqual(self.client.get(self.base + "/highlights").json()["highlights"], [highlight])
        other_base = self.base.replace(self.notebook["id"], self.other["id"])
        self.assertEqual(self.client.get(other_base + "/highlights").json()["highlights"], [])
        self.assertEqual(self.client.delete(other_base + "/highlights/" + highlight["id"]).status_code, 404)
        self.assertEqual(self.client.delete(self.base + "/highlights/" + highlight["id"]).status_code, 204)
        self.assertEqual(self.client.get(self.base + "/highlights").json()["highlights"], [])
        self.client.post(self.base + "/highlights", json=self.draft())
        self.client.delete(f"/api/notebooks/{self.notebook['id']}")
        from backend.services.notebooks import _database
        with _database() as connection:
            self.assertEqual(connection.execute("SELECT count(*) FROM pdf_highlights").fetchone()[0], 0)

    def test_version_changes_and_invalid_rectangles_are_rejected(self):
        for override in [{"page": 3}, {"page": 0}, {"text": "   "}, {"rects": []}, {"rects": [{"x": .9, "y": .1, "width": .3, "height": .1}]}, {"rects": [{"x": -.1, "y": 0, "width": .2, "height": .1}]}]:
            self.assertEqual(self.client.post(self.base + "/highlights", json=self.draft(**override)).status_code, 422)
        self.client.post(self.base + "/highlights", json=self.draft())
        write_pdf(self.pdf, "The file contents have changed and old coordinates are stale.")
        self.assertEqual(self.client.get(self.base + "/highlights").json()["highlights"], [])
        self.assertEqual(self.client.post(self.base + "/highlights", json=self.draft()).status_code, 409)

    def test_selected_chat_uses_verified_original_pages_and_returns_scope(self):
        selection = {"filename": "paper.pdf", "document_id": "paper-id", "document_version": self.info["document_version"], "page": 1, "text": "The study compares two methods"}
        url = f"/api/notebooks/{self.notebook['id']}/reading/chat"
        request = {"document_id": "paper-id", "question": "Giải thích đoạn này.", "selection": selection}
        with patch("src.rag.invoke_llm", return_value="Hai phương pháp được so sánh [S1].") as llm:
            response = self.client.post(url, json=request)
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()
        self.assertEqual(result["context"]["selection"], selection)
        self.assertEqual({item["filename"] for item in result["citations"]}, {"paper.pdf"})
        self.assertIn("The next page explains", llm.call_args.args[0])
        self.assertNotIn(str(self.data), response.text)
        exported = self.client.post("/api/export", json={"feature": "chat", "result": result})
        self.assertEqual(exported.status_code, 200)
        self.assertIn(selection["text"], exported.text)
        self.assertIn("Đoạn chọn · trang 1", exported.text)
        with patch("src.rag.invoke_llm") as llm:
            self.assertEqual(self.client.post(url, json={**request, "selection": {**selection, "text": "Invented text that is absent."}}).status_code, 422)
            self.assertEqual(self.client.post(url, json={**request, "selection": {**selection, "document_version": "0" * 64}}).status_code, 409)
            self.assertEqual(self.client.post(url, json={**request, "scope": "notebook"}).status_code, 422)
            llm.assert_not_called()

    def test_document_and_notebook_scope_are_explicit(self):
        from src.schemas import RagAnswer

        documents = [
            {"filename": "paper.pdf", "document_id": "paper-id", "pages": [1, 2], "page_count": 2, "chunk_count": 2},
            {"filename": "other.pdf", "document_id": "other-id", "pages": [1], "page_count": 1, "chunk_count": 1},
        ]
        state = self.notebook["state"]
        state["document_filenames"].append("other.pdf")
        self.client.put(f"/api/notebooks/{self.notebook['id']}", json={"title": self.notebook["title"], "icon": self.notebook["icon"], "state": state})
        url = f"/api/notebooks/{self.notebook['id']}/reading/chat"
        with patch("backend.services.core_adapter.documents", return_value=DocumentsResponse(documents=documents)), patch("src.store.list_documents", return_value=documents), patch("src.rag.answer", return_value=RagAnswer(question="Question", answer="Answer")) as answer:
            response = self.client.post(url, json={"document_id": "paper-id", "question": "Question", "scope": "document"})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(answer.call_args.kwargs["filters"], {"filename": "paper.pdf"})
            self.assertEqual(response.json()["context"]["filenames"], ["paper.pdf"])
            response = self.client.post(url, json={"document_id": "paper-id", "question": "Question", "scope": "notebook"})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(answer.call_args.kwargs["filters"], {"filenames": ["paper.pdf", "other.pdf"]})
            self.assertEqual(response.json()["context"]["filenames"], ["paper.pdf", "other.pdf"])


if __name__ == "__main__":
    unittest.main()
