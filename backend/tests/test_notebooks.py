"""Notebook lifecycle and separation, using a temporary database only."""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.main import app


class NotebookTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory(prefix="notebooks-test-")
        self.addCleanup(temporary.cleanup)
        self.path = Path(temporary.name) / "notebooks.sqlite"
        path_patch = patch("backend.services.notebooks._database_path", return_value=self.path)
        documents_patch = patch("src.store.list_documents", return_value=[])
        path_patch.start(); documents_patch.start()
        self.addCleanup(path_patch.stop); self.addCleanup(documents_patch.stop)
        self.client = self.enterContext(TestClient(app))

    def create(self, title="Sổ thứ nhất"):
        response = self.client.post("/api/notebooks", json={"title": title, "icon": "📓"})
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def test_state_and_sources_survive_reopening_without_crossing_notebooks(self):
        first, second = self.create(), self.create("Sổ thứ hai")
        state = first["state"]
        state.update(document_filenames=["first.pdf"], source_names={"first.pdf": "Nghiên cứu thứ nhất"}, selected=["first.pdf"], page="2", chat=[{
            "question": "Tóm tắt abstract", "answer": "Nội dung từ sổ thứ nhất.", "citations": [], "context": None,
        }], summary_artifacts=[{
            "id": "artifact", "title": "Tóm tắt đã lưu", "createdAt": 1,
            "sourceFilenames": ["first.pdf"], "pages": [], "topic": None,
            "result": {"scope": "document", "target": None, "summary": "Kết quả riêng.", "key_points": [], "citations": []},
        }])
        response = self.client.put(f"/api/notebooks/{first['id']}", json={"title": "Tên mới", "icon": "🔬", "state": state})
        self.assertEqual(response.status_code, 200, response.text)
        reopened = self.client.get(f"/api/notebooks/{first['id']}").json()
        self.assertEqual(reopened["title"], "Tên mới")
        self.assertEqual(reopened["source_count"], 1)
        self.assertEqual(reopened["chat_count"], 1)
        self.assertEqual(reopened["state"], state)
        self.assertEqual(self.client.get(f"/api/notebooks/{second['id']}").json()["state"], second["state"])
        summaries = self.client.get("/api/notebooks").json()["notebooks"]
        self.assertTrue(all("state" not in item for item in summaries))

    def test_delete_only_removes_target_notebook_and_does_not_reseed(self):
        first, second = self.create(), self.create("Giữ lại")
        response = self.client.delete(f"/api/notebooks/{first['id']}")
        self.assertEqual(response.status_code, 204)
        self.assertEqual(self.client.get(f"/api/notebooks/{first['id']}").status_code, 404)
        self.assertEqual([n["id"] for n in self.client.get("/api/notebooks").json()["notebooks"]], [second["id"]])

    def test_legacy_sources_migrate_once(self):
        with patch("src.store.list_documents", return_value=[{"filename": "old.pdf"}]):
            initial = self.client.get("/api/notebooks").json()["notebooks"]
            self.assertEqual(len(initial), 1)
            notebook = self.client.get(f"/api/notebooks/{initial[0]['id']}").json()
            self.assertEqual(notebook["state"]["document_filenames"], ["old.pdf"])
            self.client.delete(f"/api/notebooks/{notebook['id']}")
            self.assertEqual(self.client.get("/api/notebooks").json()["notebooks"], [])

    def test_validation_and_missing_notebook(self):
        self.assertEqual(self.client.post("/api/notebooks", json={"title": "   "}).status_code, 422)
        self.assertEqual(self.client.get("/api/notebooks/missing").status_code, 404)
        self.assertEqual(self.client.delete("/api/notebooks/missing").status_code, 404)
        self.assertEqual(self.client.put("/api/notebooks/missing", json={"title": "Title", "state": {}}).status_code, 404)
        first = self.create()
        response = self.client.put(f"/api/notebooks/{first['id']}", json={"title": "Title", "state": {
            "document_filenames": ["safe.pdf"], "source_names": {"safe.pdf": " Tên nguồn ", "other.pdf": "Không thuộc sổ"}, "selected": ["other.pdf"], "page": "1",
        }})
        self.assertEqual(response.json()["state"]["selected"], [])
        self.assertEqual(response.json()["state"]["page"], "")
        self.assertEqual(response.json()["state"]["source_names"], {"safe.pdf": "Tên nguồn"})

    def test_read_status_is_independent_from_selection_and_normalizes_members(self):
        notebook = self.create()
        path = f"/api/notebooks/{notebook['id']}"
        body = {"title": notebook["title"], "icon": notebook["icon"], "state": {
            "document_filenames": ["first.pdf", "second.pdf"], "selected": ["second.pdf"], "page": "2",
            "read_documents": ["first.pdf", "first.pdf", "outside.pdf"],
        }}
        saved = self.client.put(path, json=body)
        self.assertEqual(saved.status_code, 200, saved.text)
        state = saved.json()["state"]
        self.assertEqual(state["read_documents"], ["first.pdf"])
        self.assertEqual(state["selected"], ["second.pdf"])
        self.assertEqual(state["page"], "2")
        self.assertEqual(self.client.get(path).json()["state"], state)
        state["document_filenames"] = ["second.pdf"]
        detached = self.client.put(path, json={**body, "state": state}).json()["state"]
        self.assertEqual(detached["read_documents"], [])
        self.assertEqual(detached["selected"], ["second.pdf"])

    def test_manual_notes_persist_without_sources_and_reset_only_target_notebook(self):
        first, other = self.create(), self.create("Other notebook")
        path = f"/api/notebooks/{first['id']}"
        note = {"id": "manual-note", "title": "Ý tưởng riêng", "content": "Ghi chú tự viết.\nCần đối chiếu thêm.\n<script>plain text</script>", "createdAt": 1, "updatedAt": 2}
        state = first["state"]
        state.update(active_tool="notes", notes=[note])
        with patch("src.llm.invoke_llm") as llm:
            saved = self.client.put(path, json={"title": first["title"], "icon": first["icon"], "state": state})
            reopened = self.client.get(path).json()
            llm.assert_not_called()
        self.assertEqual(saved.status_code, 200, saved.text)
        self.assertEqual(reopened["state"]["notes"], [note])
        self.assertEqual(reopened["state"]["document_filenames"], [])
        self.assertEqual(reopened["state"]["active_tool"], "notes")
        self.assertEqual(self.client.get(f"/api/notebooks/{other['id']}").json(), other)
        edited = {**note, "title": "Tên mới", "content": "Nội dung đã sửa", "updatedAt": 3}
        state["notes"] = [edited, {**note, "id": "second-note"}]
        body = {"title": first["title"], "icon": first["icon"], "state": state}
        self.assertEqual(self.client.put(path, json=body).status_code, 200)
        self.assertEqual(self.client.get(path).json()["state"]["notes"][0], edited)
        state["notes"] = [edited]
        self.assertEqual(self.client.put(path, json=body).status_code, 200)
        self.assertEqual(len(self.client.get(path).json()["state"]["notes"]), 1)
        state.update(document_filenames=["first.pdf"], read_documents=["first.pdf"])
        self.assertEqual(self.client.put(path, json=body).status_code, 200)
        reset = self.client.post(path + "/reset", json={"confirmation": "ĐẶT LẠI"})
        self.assertEqual(reset.status_code, 200)
        self.assertEqual(reset.json()["state"]["notes"], [])
        self.assertEqual(reset.json()["state"]["read_documents"], [])
        self.assertEqual(reset.json()["id"], first["id"])
        self.assertEqual(self.client.get(f"/api/notebooks/{other['id']}").json(), other)

    def test_note_validation_and_old_workspace_defaults(self):
        notebook = self.create()
        path = f"/api/notebooks/{notebook['id']}"
        legacy = {key: value for key, value in notebook["state"].items() if key not in ("notes", "read_documents")}
        response = self.client.put(path, json={"title": notebook["title"], "state": legacy})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["state"]["notes"], [])
        self.assertEqual(response.json()["state"]["read_documents"], [])
        note = {"id": "note", "title": "Title", "content": "Content", "createdAt": 1, "updatedAt": 2}
        for notes in [[note, note], [{**note, "title": "   "}], [{**note, "content": "x" * 100001}], [{**note, "updatedAt": 0}], [{**note, "id": ""}]]:
            with self.subTest(notes_count=len(notes)):
                response = self.client.put(path, json={"title": notebook["title"], "state": {"notes": notes}})
                self.assertEqual(response.status_code, 422)
        self.assertEqual(self.client.get(path).json()["state"]["notes"], [])


if __name__ == "__main__":
    unittest.main()
