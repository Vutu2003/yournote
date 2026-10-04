# Phase 3 — Local RAG Foundation Smoke Test Report

Test date: 2026-09-30. Project root: /home/vutu/Desktop/rag_notebooklm/project.

## Test Scope

This phase tested the local foundation only:

Embedding → local Qdrant → PDF loading → chunking → embedding generation → vector storage → persistence.

It did not run similarity retrieval, Gemini, RAG answer generation, summary, quiz, flashcards, or the Gradio UI. No Gemini API request was made.

## Environment

| Item | Observed value |
|---|---|
| Python | 3.12.10 |
| Executable | /home/vutu/Desktop/rag_notebooklm/project/.venv/bin/python |
| sentence-transformers | 6.1.0 |
| qdrant-client | 1.19.1 |
| langchain-qdrant | 1.1.0 |

No packages were installed or upgraded during this phase.

## Source Configuration

| Item | Actual implementation / value |
|---|---|
| Embedding provider | local |
| Embedding model | sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 |
| Model load | Lazy first use in src.embeddings._model(), cached per process with lru_cache(maxsize=1) |
| Normalization | embed_query and embed_documents both pass normalize_embeddings=True |
| Runtime device | cuda:0, selected by Sentence Transformers; no device was forced by the test or project code |
| Vector dimension | 384, measured from the configured model at runtime |
| Default Qdrant storage | storage/qdrant, relative to project working directory; not used for this test |
| Test Qdrant storage | /tmp/rag_local_foundation_PvxT92X7/qdrant, set with a process-only RAG_STORAGE_DIR override |
| Collection | rag_chunks, the configured default name inside isolated test storage |
| Distance metric | Cosine |
| Collection handling | ensure_collection creates a missing collection using the measured vector dimension and requests payload indexes; it reuses an existing collection when recreate=False |
| PDF loader | langchain_community.document_loaders.PyPDFLoader |
| Text splitter | RecursiveCharacterTextSplitter; separators: double newline, newline, period plus space, space, empty string |
| Chunk size / overlap | 1500 / 200 |
| Chunk metadata | document_id, filename, source, page, chunk_id, section |
| Document ID | First 16 hex characters of SHA-1 of filename and file size |
| Chunk/point IDs | chunk_id is document_id:page:counter; point ID is UUIDv5 derived from chunk_id |
| Application upload/index path | src.indexing.save_and_ingest_pdf(file_bytes, filename), the function used by app.py |
| Existing-point behavior | add_documents with deterministic point IDs upserts matching IDs; the upload path does not delete obsolete points from prior document versions |

The test set RAG_STORAGE_DIR and RAG_DATA_DIR only for its child Python process and verified both overrides before opening Qdrant. Project configuration files and .env were not edited.

## Test PDF

- File: /tmp/rag_local_foundation_PvxT92X7/foundation_smoke.pdf
- Origin: generated specifically for this phase because the only pre-existing local PDF was 38 pages, larger than needed for a smoke test.
- Size: 806 bytes.
- Pages: 1.
- Content: three short, harmless lines describing the local RAG smoke test.
- The application's upload function copied it to /tmp/rag_local_foundation_PvxT92X7/data/foundation_smoke.pdf through the process-only RAG_DATA_DIR override. It was not placed in the project's production data directory.

## Embedding Runtime Test

| Check | Result |
|---|---|
| Configured model loaded through src.embeddings | PASS |
| One short query string embedded | PASS |
| Numeric finite vector | PASS |
| Dimension | 384 |
| Runtime device | cuda:0 |
| Normalization | Source requests normalized embeddings; measured L2 norm of test vector was 1.0 |

This was a minimal model-load and embedding test, not a performance benchmark.

## Qdrant Initialization

| Check | Result |
|---|---|
| Local client opened through src.store.get_client | PASS |
| Isolated storage directory accessible | PASS |
| Test collection existed before test | NO |
| Collection created through ensure_collection(recreate=False) | PASS |
| Collection vector size / distance | 384 / Cosine |
| Points before ingestion | 0 |
| Existing project data detected | Default project storage/qdrant and data/ paths were absent before and after the test |

A fresh temporary storage directory was used. No existing collection was reset or deleted. The project default Qdrant path was not opened.

## PDF Ingestion and Chunking

| Check | Result |
|---|---|
| PDF opened and text extracted | PASS |
| Pages extracted | 1 |
| RecursiveCharacterTextSplitter ran | PASS |
| Nonempty chunks created | 1 |
| Required metadata attached | PASS |
| Observed metadata keys | chunk_id, document_id, filename, page, section, source |

The fixture was checked with build_chunks first, then the real application upload path save_and_ingest_pdf was run with the same PDF bytes. The upload path reported one indexed chunk.

## Vector Storage

| Check | Result |
|---|---|
| Chunk embedding through the project adapter | PASS |
| Qdrant write through the project indexing path | PASS |
| Test points stored | 1 |
| Stored point inspection | Point exists |
| Stored vector dimension | 384 |
| Payload keys | metadata, page_content |
| Stored metadata keys | chunk_id, document_id, filename, page, section, source |

No full vector or full document text was printed or included in this report.

## Persistence

src.store.close_client() closed the cached local client. Reopening the same isolated storage through src.store.get_client() succeeded, and the collection still contained one point.

- Reopen: PASS
- Stored points still present: YES
- Persisted point count: 1

No semantic retrieval was performed.

## Result

PASS

The configured model loaded and generated an embedding; local Qdrant initialized; the PDF was loaded and split; a vector was written; and the point persisted after closing and reopening the client.

## Errors / Warnings

- The Hugging Face Hub warned that model access was unauthenticated and may have lower rate limits. Model load succeeded.
- Local Qdrant warned that payload indexes have no effect in embedded/local mode. Collection creation and vector storage still succeeded.
- No test error occurred.

## Source Changes

NONE.

Temporary artifacts from this phase are separate from source: the generated PDF, its upload copy, and local Qdrant files under /tmp/rag_local_foundation_PvxT92X7. The model's normal Hugging Face cache may also have been used. This report is the only new project file from this phase.

## Git Safety

- No source code, app.py, requirements.txt, static files, or prompts changed in this phase; git diff for those paths was empty.
- .env was not read aloud or edited and remains ignored by Git.
- No commit, push, pull, or other mutating Git command was run.
- Existing project storage/qdrant data was not deleted or modified; the default path was absent before and after testing.
- Prior Git status already showed a modified .gitignore and three untracked reports from earlier phases. Those were not changed by this phase.

## Recommended Next Step

Run a separately authorized PHASE 4 — Retrieval + End-to-End RAG Q&A Smoke Test: indexed PDF → similarity retrieval → citation/source construction → prompt rendering → Gemini → final RagAnswer. Phase 4 was not run here.
