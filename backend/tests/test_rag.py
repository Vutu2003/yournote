"""Retrieval regressions using an isolated, in-memory Qdrant collection."""

import unittest
from unittest.mock import patch

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient, models

from src import rag


class FixedEmbeddings(Embeddings):
    def embed_documents(self, texts):
        return [[0.0, 1.0] if "overview" in text else [1.0, 0.0] for text in texts]

    def embed_query(self, text):
        return [1.0, 0.0]


class AbstractRetrievalTests(unittest.TestCase):
    def setUp(self):
        self.client = QdrantClient(":memory:")
        self.client.create_collection("test", vectors_config=models.VectorParams(size=2, distance=models.Distance.COSINE))
        self.store = QdrantVectorStore(client=self.client, collection_name="test", embedding=FixedEmbeddings())
        self.store.add_documents([
            self.document("paper.pdf", 1, 0, "Title and authors\nAn unlabelled overview of the study."),
            self.document("paper.pdf", 1, 1, "Our overview finds reduced error.\n1. Introduction: background."),
            self.document("paper.pdf", 5, 2, "Table 1: Detailed experimental results."),
            self.document("other.pdf", 1, 0, "Another overview that must stay outside the selection."),
        ])
        self.client_patch = patch("src.store.get_client", return_value=self.client)
        self.store_patch = patch("src.rag.get_vector_store", return_value=self.store)
        self.client_patch.start()
        self.store_patch.start()
        self.addCleanup(self.client.close)
        self.addCleanup(self.client_patch.stop)
        self.addCleanup(self.store_patch.stop)

    @staticmethod
    def document(filename, page, index, text):
        return Document(page_content=text, metadata={
            "document_id": filename, "filename": filename, "source": filename,
            "page": page, "chunk_id": f"{filename}:{page}:{index}",
        })

    def test_abstract_recovers_opening_chunks_missed_by_similarity(self):
        filters = {"filename": "paper.pdf"}
        question = "hãy giúp tôi tóm tắt nội dung của phần abstract trong tài liệu trên"
        dense = rag.retrieve(question, k=1, filters=filters, collection_name="test")
        self.assertEqual(dense[0].metadata.page, 5)
        with patch("src.rag.invoke_llm", return_value="Nghiên cứu giảm sai số [S2].") as llm:
            result = rag.answer(question, k=1, filters=filters, collection_name="test")
        self.assertEqual([c.metadata.page for c in result.chunks], [1, 1])
        self.assertEqual({c.filename for c in result.citations}, {"paper.pdf"})
        self.assertEqual(len(result.citations), 2)
        prompt = llm.call_args.args[0]
        self.assertIn("An unlabelled overview", prompt)
        self.assertIn("Our overview finds reduced error", prompt)
        self.assertNotIn("Table 1", prompt)
        self.assertIn("Some papers have an unlabelled abstract", prompt)

    def test_abstract_keeps_explicit_page_filter(self):
        with patch("src.rag.invoke_llm", return_value="Không có abstract."):
            result = rag.answer("Tóm tắt phần abstract", filters={"filename": "paper.pdf", "page": 5}, collection_name="test")
        self.assertEqual([c.metadata.page for c in result.chunks], [5])

    def test_ordinary_question_keeps_similarity_retrieval(self):
        with patch("src.rag.fetch_all_chunks") as scroll, patch("src.rag.invoke_llm", return_value="Kết quả [S1]."):
            result = rag.answer("Kết quả thí nghiệm?", k=1, filters={"filename": "paper.pdf"}, collection_name="test")
        scroll.assert_not_called()
        self.assertEqual([c.metadata.page for c in result.chunks], [5])

    def test_no_context_does_not_call_llm(self):
        with patch("src.rag.invoke_llm") as llm:
            result = rag.answer("Tóm tắt abstract", filters={"filename": "missing.pdf"}, collection_name="test")
        llm.assert_not_called()
        self.assertEqual(result.citations, [])
        self.assertIn("không có đủ thông tin", result.answer)

    def test_labelled_abstract_continues_to_next_page(self):
        self.store.add_documents([
            self.document("labelled.pdf", 1, 0, "Title and contents"),
            self.document("labelled.pdf", 2, 1, "A B S T R A C T\nThe overview starts here."),
            self.document("labelled.pdf", 3, 2, "The overview concludes here.\nIntroduction\nBackground"),
            self.document("labelled.pdf", 4, 3, "References"),
        ])
        with patch("src.rag.invoke_llm", return_value="Tóm tắt [S1][S2]."):
            result = rag.answer("Tóm tắt mục tóm tắt", filters={"filename": "labelled.pdf"}, collection_name="test")
        self.assertEqual([c.metadata.page for c in result.chunks], [2, 3])


if __name__ == "__main__":
    unittest.main()
