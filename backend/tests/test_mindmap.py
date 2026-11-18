"""Grounding, reduction, API persistence and export without provider calls."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend.main import app
from backend.schemas.api import DocumentsResponse, MindMapResponse
from src.config import settings
from src.mindmap import _ground_tree, generate_mindmap
from src.schemas import ChunkMetadata, RetrievedChunk


def tree(markers=("S1",), label="Nội dung nghiên cứu"):
    return {"root": {"label": label, "description": "Tổng quan", "children": [
        {"label": "Phương pháp", "description": "So sánh hai phương pháp.", "source_markers": list(markers), "children": []},
    ]}}


def chunks(count):
    return [RetrievedChunk(text=f"Source text number {index}", score=0, metadata=ChunkMetadata(
        filename="paper.pdf", document_id="paper", source="/private/path/paper.pdf",
        page=index, chunk_id=f"paper:{index}:{index}",
    )) for index in range(1, count + 1)]


class MindMapGenerationTests(unittest.TestCase):
    def test_selected_material_and_real_references_are_used(self):
        payload = tree(("S1", "S999"))
        with patch("src.learning.fetch_all_chunks", return_value=chunks(2)) as fetch, patch("src.mindmap.invoke_llm", return_value=json.dumps(payload)) as llm:
            result = generate_mindmap(filters={"filename": "paper.pdf", "page": 1})
        fetch.assert_called_once_with(filters={"filename": "paper.pdf", "page": 1})
        self.assertEqual(result.root.source_markers, ["S1"])
        self.assertEqual(result.root.children[0].source_markers, ["S1"])
        self.assertEqual([citation.source_marker for citation in result.citations], ["S1"])
        self.assertIn("Source text number 2", llm.call_args.args[0])
        self.assertNotIn("/private/path", llm.call_args.args[0])

    def test_topic_uses_scoped_retrieval(self):
        with patch("src.learning.retrieve", return_value=chunks(1)) as retrieve, patch("src.mindmap.invoke_llm", return_value=json.dumps(tree())):
            result = generate_mindmap(query="Methods", filters={"filename": "paper.pdf"}, k=3)
        retrieve.assert_called_once_with("Methods", k=3, filters={"filename": "paper.pdf"})
        self.assertEqual(result.scope, "query")
        self.assertEqual(result.target, "Methods")

    def test_all_batches_keep_global_ids_through_reduction(self):
        outputs = [tree(("S1",)), tree(("S3",)), tree(("S5",)), tree(("S1", "S3", "S5"))]
        with patch.object(settings, "mindmap_batch_size", 2), patch("src.learning.fetch_all_chunks", return_value=chunks(5)), patch("src.mindmap.invoke_llm", side_effect=[json.dumps(output) for output in outputs]) as llm:
            result = generate_mindmap(filters={"filename": "paper.pdf"})
        prompts = [call.args[0] for call in llm.call_args_list]
        self.assertEqual(len(prompts), 4)
        self.assertIn("[source=S3]", prompts[1])
        self.assertNotIn("[source=S1]", prompts[1])
        self.assertIn("Source text number 5", prompts[2])
        self.assertIn('"S5"', prompts[3])
        self.assertEqual([(citation.source_marker, citation.page) for citation in result.citations], [("S1", 1), ("S3", 3), ("S5", 5)])

    def test_mindmap_batch_size_reduces_calls_without_skipping_chunks(self):
        source = chunks(25)
        outputs = [tree(("S1",)), tree(("S25",)), tree(("S1", "S25"))]
        with patch.object(settings, "mindmap_batch_size", 24), patch("src.learning.fetch_all_chunks", return_value=source), patch("src.mindmap.invoke_llm", side_effect=[json.dumps(output) for output in outputs]) as llm:
            generate_mindmap(filters={"filename": "paper.pdf"})
        prompts = [call.args[0] for call in llm.call_args_list]
        self.assertEqual(len(prompts), 3)
        for index in range(1, 25):
            self.assertIn(f"[source=S{index}]", prompts[0])
        self.assertIn("[source=S25]", prompts[1])

    def test_unsupported_leaves_and_malformed_outputs_are_rejected(self):
        for payload in [[], {}, tree(()), tree(("S999",)), {"root": {"label": "Only root", "source_markers": ["S1"]}}]:
            with self.subTest(payload=payload), self.assertRaises(RuntimeError):
                _ground_tree(payload, {"S1"})
        with patch("src.learning.fetch_all_chunks", return_value=[]), patch("src.mindmap.invoke_llm") as llm:
            with self.assertRaises(RuntimeError):
                generate_mindmap(filters={"filename": "empty.pdf"})
        llm.assert_not_called()

    def test_tree_size_depth_and_blank_labels_are_bounded(self):
        deep = {"label": "Level", "source_markers": ["S1"]}
        for _ in range(4):
            deep = {"label": "Level", "children": [deep]}
        wide = {"label": "Root", "children": [{"label": "Branch", "children": [{"label": "Leaf"} for _ in range(8)]} for _ in range(8)]}
        for root in [deep, wide, {"label": "   "}, {"label": "Root", "children": [{"label": "Leaf"}] * 9}]:
            with self.subTest(root=root), self.assertRaises(ValidationError):
                MindMapResponse(scope="filter", root=root)


class MindMapAPITests(unittest.TestCase):
    def setUp(self):
        root = Path(self.enterContext(TemporaryDirectory(prefix="mindmap-test-")))
        self.enterContext(patch("backend.services.notebooks._database_path", return_value=root / "notebooks.sqlite"))
        self.enterContext(patch("src.store.list_documents", return_value=[]))
        self.enterContext(patch("backend.services.core_adapter.documents", return_value=DocumentsResponse(documents=[{
            "filename": "paper.pdf", "document_id": "paper", "pages": [1], "page_count": 1, "chunk_count": 1,
        }])))
        self.client = self.enterContext(TestClient(app))

    def test_transport_export_reopen_isolation_and_notebook_reset(self):
        with patch("src.store.list_documents", return_value=[{"filename": "paper.pdf", "pages": [1]}]), patch("src.learning.fetch_all_chunks", return_value=chunks(1)), patch("src.mindmap.invoke_llm", return_value=json.dumps(tree())):
            response = self.client.post("/api/mindmap", json={"filenames": ["paper.pdf"], "pages": [1]})
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()
        self.assertNotIn("/private/path", response.text)
        exported = self.client.post("/api/export", json={"feature": "mindmap", "result": result})
        self.assertEqual(exported.status_code, 200)
        self.assertIn("Phương pháp", exported.text)
        self.assertIn("[S1] paper.pdf p.1", exported.text)
        self.assertIn('filename="mindmap.md"', exported.headers["content-disposition"])
        first = self.client.post("/api/notebooks", json={"title": "With mind map"}).json()
        other = self.client.post("/api/notebooks", json={"title": "Untouched"}).json()
        state = first["state"]
        state.update(active_tool="mindmap", document_filenames=["paper.pdf"], selected=["paper.pdf"], mindmap_artifacts=[{
            "id": "map-1", "title": result["root"]["label"], "createdAt": 1,
            "sourceFilenames": ["paper.pdf"], "pages": [1], "topic": None, "result": result,
        }])
        path = f"/api/notebooks/{first['id']}"
        saved = self.client.put(path, json={"title": first["title"], "icon": first["icon"], "state": state})
        self.assertEqual(saved.status_code, 200, saved.text)
        self.assertEqual(self.client.get(path).json()["state"], state)
        self.assertEqual(self.client.get(f"/api/notebooks/{other['id']}").json(), other)
        reset = self.client.post(path + "/reset", json={"confirmation": "ĐẶT LẠI"})
        self.assertEqual(reset.status_code, 200)
        self.assertEqual(reset.json()["state"]["mindmap_artifacts"], [])
        self.assertEqual(self.client.get(f"/api/notebooks/{other['id']}").json(), other)


if __name__ == "__main__":
    unittest.main()
