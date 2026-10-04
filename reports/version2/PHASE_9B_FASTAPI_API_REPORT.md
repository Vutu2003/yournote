# Phase 9B — FastAPI API Contract and Core Adapter Report

## Phase Result

**PASS** — 2026-10-04. All required endpoints are implemented, the four generation endpoints passed real HTTP/core/Gemini integration, and the existing indexed data is unchanged. Successful real PDF ingestion was deliberately deferred; upload validation and delegation were verified without writing to the real baseline.

## Scope

Implemented a thin transport layer under `backend/` and this single report. No React feature UI, database, migration, model change, core rewrite, commit or push. Phase 10 was not started. No dependencies were installed or updated.

## Architecture

```text
Browser → React/TypeScript/Vite → HTTP/JSON → FastAPI
                                             ↓
                                  backend/services/core_adapter.py
                                             ↓
                          existing src.store/indexing/rag/learning/export
                                             ↓
                               local Qdrant/filesystem + Gemini
```

React remains the Phase 9A scaffold. This phase exercised FastAPI with a local HTTP client. Generation credentials are read by the existing server-side core; there is no API request field for a Gemini key.

## Core Protection

SHA-256 comparison against a snapshot taken before implementation confirmed **48 protected files unchanged**, covering `src/` including prompts, `app.py`, `requirements.txt`, `.env`, `static/`, existing PDFs in `data/`, and frontend source/configuration/lockfiles. Generated Python caches, frontend dependencies and build outputs were excluded from that source snapshot.

The existing Qdrant collection was only read. After orderly API shutdown, all **132 point IDs, payloads and vectors** matched the before snapshot exactly. No collection recreation, deletion, ingestion, document ID change or embedding/model setting change occurred. The Gradio fallback was neither modified nor started.

## Backend Structure

```text
backend/
├── __init__.py
├── main.py
├── requirements-api.txt                 # unchanged Phase 9A dependencies
├── api/
│   ├── __init__.py
│   └── routes/
│       ├── __init__.py
│       ├── documents.py
│       ├── chat.py
│       ├── learning.py
│       └── exports.py
├── schemas/
│   ├── __init__.py
│   └── api.py
├── services/
│   ├── __init__.py
│   └── core_adapter.py
└── tests/
    ├── __init__.py
    └── test_api.py
```

Core imports are lazy: a cold import, health request and OpenAPI request did not import `src.store`, `src.embeddings` or `src.llm`. Synchronous routes execute through FastAPI's thread pool. A process-local reentrant lock serializes core access, including indexing and shutdown, without changing core algorithms. Lifespan shutdown closes the existing cached Qdrant client.

Launch from `project/`, using a **single worker** because embedded Qdrant holds an exclusive process lock:

```bash
.venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

The existing `scripts/dev_backend.sh` remains available and unchanged. The temporary integration server has been stopped and its Qdrant client closed.

## API Contract

| Method | Endpoint | Purpose | Core function | Status |
|---|---|---|---|---|
| GET | `/api/health` | HTTP readiness without AI loading | None | PASS, HTTP 200 |
| GET | `/api/documents` | Indexed PDF metadata and pages | `src.store.list_documents()` | PASS, HTTP 200, 3 documents |
| POST | `/api/documents/upload` | One multipart PDF | `src.indexing.save_and_ingest_pdf()` | PASS for validation/delegation; real successful ingestion deferred |
| POST | `/api/chat` | Grounded Q&A | `src.rag.answer()` | PASS, HTTP 200 |
| POST | `/api/summary` | Grounded summary | `src.learning.summarize()` | PASS, HTTP 200 |
| POST | `/api/quiz` | Generate quiz data | `src.learning.generate_quiz()` | PASS, HTTP 200 |
| POST | `/api/flashcards` | Generate card data | `src.learning.generate_flashcards()` | PASS, HTTP 200 |
| POST | `/api/export` | Canonical Markdown attachment | `src.export.export(..., fmt="md")` | PASS, HTTP 200 for all four generated results |

## Request / Response Schemas

Public models live in `backend/schemas/api.py`; private core models are not automatically published. Unknown JSON fields are rejected.

### Shared selection and validation

- `filenames`: required list of 1–64 indexed PDF basenames; trimmed and deduplicated, with no paths or control characters. Individual names are limited to 255 characters and must end in `.pdf`, case-insensitively. Empty selection is HTTP 422; an unknown indexed filename is HTTP 404.
- `pages`: optional list, default `[]` for all matching pages. At most **one positive integer page**, and only with exactly one selected PDF. Multiple pages or a page with multiple PDFs are HTTP 422. A page absent from indexed metadata is HTTP 404. This restriction preserves the core's actual filter capabilities rather than silently dropping a requested filter.
- All integer controls are strict: booleans and numeric strings are rejected.
- `topic`: optional string for learning, trimmed; blank becomes `null`; maximum 10,000 characters. A non-empty topic maps to core `query` and therefore changes retrieval scope. It is not a separate topic-only generation instruction.
- Learning `k`: optional strict integer `1..128`, default `null` to preserve the core fallback. It affects query retrieval only. Without a topic, the core uses all matching chunks and ignores `k`.

| Endpoint | Request model / extra fields | Response model / fields |
|---|---|---|
| Health | No body | `HealthResponse`: `status: "ok"` |
| Documents | No body | `DocumentsResponse`: `documents[]` with `filename`, `document_id`, `pages`, `page_count`, `chunk_count` |
| Upload | Multipart field `file` | `UploadResponse`: `filename`, `chunks_indexed` |
| Chat | `ChatRequest`: selection + nonblank `question` (max 10,000), `k=6` (`1..64`) | `ChatResponse`: `question`, `answer`, `citations[]` |
| Summary | `SummaryRequest`: selection + `topic`, `k` | `SummaryResponse`: `scope`, `target`, `summary`, `key_points[]`, `citations[]` |
| Quiz | `QuizRequest`: learning fields + `count=3` (`1..50`) | `QuizResponse`: `scope`, `target`, `items[]`, `citations[]` |
| Flashcards | `FlashcardsRequest`: learning fields + `count=3` (`1..100`) | `FlashcardsResponse`: `scope`, `target`, `cards[]`, `citations[]` |
| Export | Discriminated union: `feature` + matching validated `result` | UTF-8 `text/markdown` attachment |

Every public citation preserves `source_index`, `source_marker` (e.g. `S1`, without brackets), `filename`, `page`, `chunk_id`, optional `section` and optional `source_text`. **Source chunk text is deliberately included** for expandable source views and complete exports. Chat omits the private `chunks` list, including `metadata.source` absolute paths and other unnecessary internal metadata. No vectors are published.

Quiz items preserve `question`, exactly four `options`, `correct_index` (`0..3`), `explanation`, `source_markers`, optional `difficulty` and `topic`. Cards preserve `front`, `back`, optional `hint`, `topic`, and `source_markers`. Learning responses retain the core scope enum `query|document|filter|corpus`; the current HTTP selection path normally produces `filter` or `query` because it passes filters rather than a `document` argument.

Example Chat request using the tested PDF:

```json
{
  "question": "How many distinct types of nonlinear dynamics did the complexity analyses show in short heart period variability recordings?",
  "filenames": ["4 Complexity analyses show two distinct types of nonlinear dynamics in short heart period variability recordings.pdf"],
  "pages": [],
  "k": 6
}
```

Summary uses the same `filenames` and `pages`, with optional `topic`/`k`; Quiz and Flashcards additionally accept `count`. There are no arbitrary collection names, filesystem paths, credential fields or frontend interaction-state fields in these generation contracts.

## Documents API

Uses the existing metadata scroll and aggregation in `list_documents()` directly. The actual current baseline is **3 PDFs and 132 points**, rather than the historical 2 PDFs/100 points. Returned page lists and counts come from indexed metadata; no PDF parsing, embeddings, inferred document IDs or vector retrieval are needed for this endpoint.

## Upload API

Accepts one `file` part. Checks filename, `.pdf` extension, content type (`application/pdf`, `application/octet-stream`, or unspecified), non-empty bytes, a **25 MiB** limit and a PDF header within the first 1,024 bytes. The unchanged core performs substantive PDF parsing, splitting, embedding and storage.

The response uses the actual core return shape: `filename` and `chunks_indexed`. The core does not return `document_id`; clients can obtain it through `GET /api/documents` afterward. No ID is fabricated.

Real HTTP tests rejected `.txt`, empty PDF and missing-PDF-header uploads with HTTP 400 and no ingestion. Contract tests additionally covered path-like filenames, wrong content type, size-limit handling and a missing multipart field (HTTP 422).

For success delegation and failure handling, only `src.indexing.save_and_ingest_pdf` was substituted in focused tests. These verified exact byte/name forwarding, response serialization and safe HTTP 500 without writing PDFs or Qdrant points. **Real successful upload integration remains deferred** to a later isolated/frontend test. Existing core overwrite/stale-point/nontransactional behavior was not changed.

## Chat API

Builds filters with existing `src.filters.filters_to_dict()` and calls `answer(question, k, filters)`. Single-PDF selection normalizes to `filename`; multi-PDF selection remains `filenames`; supported page selection maps to singular `page`. Indexed document/page existence is checked before generation.

Exactly one grounded Chat HTTP request used the example above. Result: HTTP 200, **6 citations**, approximately **9.37 seconds**, and the answer:

> Các phép đo độ phức tạp đã chỉ ra sự hiện diện của hai loại động lực học phi tuyến tính (HP) khác biệt [S2].

This matches the expected two distinct types. Markers and answer text were preserved; factual grounding was checked for this known question, not asserted for every future generated claim. With no retrieved context, the unchanged core's insufficient-context result is returned normally without a Gemini call.

## Summary API

Calls `summarize(query=topic, filters=..., k=...)`. Exactly one no-topic request selected the same PDF's **35 chunks**. Result: HTTP 200, non-empty summary, **7 key points**, **35 citations**, scope `filter`, approximately **12.79 seconds**. The original batch size of 10 produced four map calls and one reduce call. No map-reduce behavior or generated text was changed.

## Quiz API

Calls `generate_quiz(count=..., query=topic, filters=..., k=...)`. Exactly one request asked for three questions over the same PDF. Result: HTTP 200, **3 items**, four options per item, valid `correct_index`, non-empty explanations, and non-empty item markers resolving to the **35 returned citations**, approximately **3.47 seconds**.

The API generates the complete set only. React will own selected options, answer checking, reveal and Previous/Next. Those interactions require zero additional Gemini calls.

## Flashcards API

Calls `generate_flashcards(count=..., query=topic, filters=..., k=...)`. Exactly one request asked for three cards over the same PDF. Result: HTTP 200, **3 cards**, non-empty fronts/backs, and non-empty card markers resolving to the **35 returned citations**, approximately **2.77 seconds**. Optional hint/topic fields are retained. Reveal/navigation state belongs to React.

## Export Decision

**Implemented** `POST /api/export` with `{ "feature": "chat|summary|quiz|flashcards", "result": ... }`. Each discriminator selects the corresponding public response model. The adapter converts validated data to the appropriate core model and calls `export(..., fmt="md")` **without an output path**.

No persistence, file lookup or client-selected server path is involved. Responses use a fixed feature-derived download name, such as `summary.md`. This endpoint validates structure and renders client-submitted results; it does not authenticate their origin or re-check factuality.

All four real generated results exported successfully. Each returned citation's chunk ID and source text remained in the canonical Markdown. Observed attachment sizes: Chat **10,694 bytes**, Summary **58,320**, Quiz **65,268**, Flashcards **67,158**. Invalid result structure and attempted `output` fields were rejected with HTTP 422. Exports made no Gemini requests and wrote no files.

## Error Handling

| Status | Policy |
|---|---|
| 400 | Invalid upload name/type/content/header/size |
| 404 | Selected PDF or selected page not present in indexed metadata |
| 422 | JSON/multipart schema validation, unsupported filter combination, invalid ranges, unknown fields |
| 500 | Unexpected core/runtime/provider failure; generic safe client message |

Ordinary errors return `{ "detail": "safe message" }`. Validation returns `{ "detail": [{ "loc": [...], "msg": "...", "type": "..." }] }`; raw input and validation contexts are omitted. Core exceptions are logged with a server-side traceback and configured Gemini-key redaction. Clients receive `Unable to complete the operation. Please try again.` rather than provider details, paths or traceback. The targeted failure test verified this response and key redaction. No speculative provider-specific HTTP 503 mapping was added.

## CORS

Explicit origins only: `http://localhost:5173` and `http://127.0.0.1:5173`. Credentials disabled; methods `GET`, `POST`, `OPTIONS`; requested non-safelisted header `Content-Type`. `Content-Disposition` is exposed so React can read the Markdown download filename.

Both allowed POST preflights passed; a disallowed origin returned HTTP 400 without an allow-origin header. Actual export responses exposed the attachment header. No wildcard origin or credential handling was introduced.

## OpenAPI

`GET /openapi.json` and `/docs` returned HTTP 200. OpenAPI contains **8 paths**, endpoint summaries, explicit public response schemas, generation request schemas, multipart upload, error schemas and the discriminated export request. The export HTTP 200 content schema is `text/markdown`. Page restrictions, topic semantics and core limitations are documented in schema/endpoint descriptions. No secret values or internal runtime paths are embedded in these contracts.

## Runtime Integration Tests

| Check | Actual result |
|---|---|
| Cold import/health/OpenAPI | PASS; no AI/core runtime imports |
| Local Uvicorn startup/shutdown | PASS; 127.0.0.1:8000; graceful lifespan close |
| Documents | PASS; HTTP 200; 3 PDFs / 132 indexed chunks |
| Chat | PASS; exactly one request; correct two-types answer; 6 citations |
| Summary | PASS; exactly one request; 7 key points; 35 citations |
| Quiz | PASS; exactly one request, count 3; 3 valid items |
| Flashcards | PASS; exactly one request, count 3; 3 valid cards |
| Upload validation | PASS; three real invalid HTTP uploads rejected; no successful ingestion |
| Markdown | PASS; all four generated payloads downloadable through the API |
| CORS/docs/OpenAPI | PASS over real HTTP and TestClient |
| Contract tests | PASS; 13 unittest tests, including validation, unknown selections, safe failures, filters and export |
| Compile/import | PASS; all backend Python modules compiled and imported |
| `.venv/bin/python -m pip check` | PASS; `No broken requirements found.` |

Test command:

```bash
.venv/bin/python -m unittest discover -s backend/tests -v
```

Documents, filter normalization and exports exercised real core code. Only successful/failing upload delegation was substituted to protect the real baseline. Generation integration used actual existing retrieval, embeddings, learning functions and Gemini responses, without mocks or repeat requests.

Sandbox restrictions stalled the initial TestClient checks; those processes were terminated and the same checks ran successfully with local socket access. No provider requests occurred in the stalled checks. Frontend build/lint were not repeated because frontend files remained unchanged and this phase has no React implementation.

## Gemini Call Accounting

Temporary forwarding instrumentation outside the repository recorded both `generate_content` invocations and actual HTTP sends to Gemini, labelled by the incoming endpoint. It returned the original SDK responses and did not modify any core file or substitute provider output.

| Feature | Real API generation requests | Completed Gemini calls | Gemini HTTP sends |
|---|---:|---:|---:|
| Chat | 1 | 1 | 1 |
| Summary | 1 | 5: four map + one reduce | 5 |
| Quiz | 1 | 1 | 1 |
| Flashcards | 1 | 1 | 1 |
| **Total** | **4** | **8** | **8** |

All eight provider HTTP responses were 200. No failed calls, retries, extra generation requests or answer-check/reveal calls were observed. Metadata, health, validation, docs, CORS and export checks made no Gemini calls. Test timing is one observed run, not a benchmark.

## Qdrant Integrity

| Indexed PDF | Before chunks | After chunks | Pages |
|---|---:|---:|---|
| `2 Heart rate variability in normal and pathological sleep.pdf` | 65 | 65 | 1–11 |
| `4 Complexity analyses show two distinct types of nonlinear dynamics in short heart period variability recordings.pdf` | 35 | 35 | 1–7 |
| `Healthcare Tech Letters - 2018 - Islam - Cascade and parallel combination  CPC  of adaptive filters for estimating heart.pdf` | 32 | 32 | 1–7 |
| **Total** | **132** | **132** | **3 PDFs** |

Collection remains `rag_chunks`. Before/after document metadata, point IDs, payloads and vectors compared equal. Zero real successful uploads, re-indexes, deletions or migrations were performed.

## Security Validation

Representative JSON responses and all four Markdown attachments were scanned for the configured Gemini key, `GEMINI_API_KEY`, `.env` content, absolute workspace/data/storage paths, raw traceback, vector fields and private chunk metadata: **PASS**. Public citations intentionally retain PDF source text, not local source paths.

Frontend source remained unchanged and contained neither the configured key nor `GEMINI_API_KEY`. Server runtime logs passed the key-exposure scan. Failure and unknown-field tests confirmed a safe 500 body and omission of submitted secret-like validation values. No key was printed, placed in frontend state/types, emitted in exports or added to API models.

## Frontend Contract Readiness

**Ready for Phase 10 — React API Integration Foundation.** OpenAPI and the explicit public Pydantic contracts can guide typed clients for all current features. React should fetch documents, send explicit selection, handle 400/404/422/500, store generated JSON locally, manage quiz/card interaction state without API calls, and download Markdown through `/api/export`.

The frontend still has its Phase 9A health-only type stub. No feature components, API client expansion, styles or workflow state were implemented in this task.

## Files Added / Modified

- Modified `backend/main.py`: routing, CORS, lifecycle, public health and safe errors.
- Added `backend/schemas/api.py`: request/response/error/export contracts and transport validation.
- Added `backend/services/core_adapter.py`: existing-function delegation, supported filters and safe serialization.
- Added `backend/api/routes/documents.py`, `chat.py`, `learning.py`, `exports.py`.
- Added `backend/tests/__init__.py` and `backend/tests/test_api.py`.
- Added this report only: `reports/version2/PHASE_9B_FASTAPI_API_REPORT.md`.

Existing package markers and `backend/requirements-api.txt` were preserved. Scripts, frontend, root dependencies and application core were not changed.

## Core Diff Audit

**Phase 9B core changes: NONE.** `git diff -- src/` and `git diff -- requirements.txt` were empty. `app.py` and `static/style.css` already contained Phase 8 changes relative to Git HEAD; their bytes match the pre-Phase-9B snapshot, so those existing changes were preserved rather than reverted. The existing modified `.gitignore` and untracked scaffold/reports/scripts also predated this task.

The 48-file protected snapshot independently confirms zero Phase 9B edits to protected areas, including `.env`, prompts, PDFs and frontend. Qdrant content equality was checked separately. No commit or push occurred.

## Known Limitations

- Current core supports one page for one PDF; arbitrary page lists/page filters across multiple PDFs are rejected at the API boundary. Unselected global-corpus generation is not exposed by these HTTP requests.
- Embedded Qdrant requires a single server process. Core access is serialized within that process; this phase does not introduce a remote store or throughput changes.
- Real successful upload integration is deferred. The header check is not a complete PDF validator; the core parser still controls parse/index failures. Existing same-name overwrite, stale-point and nontransactional ingestion behavior remain.
- Without a topic, learning uses all selected chunks. Summary may make multiple map/reduce calls; quiz/cards may create large prompts. There is no new corpus/context cap or generation retry.
- Core validation can return fewer quiz items/cards than requested; this observed run returned three of each. Citation presence and marker validity do not establish universal factual support.
- API export renders client-supplied validated data without persistence or provenance verification. Full source text is deliberately returned/exported, so frontend presentation should keep it collapsed by default.
- No React feature integration or browser UI test was performed in this backend phase.

## Result

**PASS** for API startup, OpenAPI/docs, real document listing, all four real generation endpoints, upload contract validation/delegation, canonical exports, error handling, CORS, unchanged core, unchanged Qdrant contents and credential/path/vector/traceback response checks. The successful real-upload test remains explicitly deferred to preserve existing indexed data.

Permanent report files created in Phase 9B: **1**.

## Recommended Next Step

**PHASE 10 — React API Integration Foundation**: connect typed API clients, source selection and generated-result state, with loading/error states and local quiz/card interaction. Visual polish can follow. Phase 10 has **not** been started.
