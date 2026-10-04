# Phase 10 — React Research Notebook Implementation Report

## Phase Result

**PASS** — 2026-10-04. The React Research Notebook works against the existing FastAPI contract. Sources, Chat, Summary, Quiz, Flashcards, downloads, local interactions, and requested responsive layouts passed browser verification. One real successful upload passed against an isolated copy of the indexed baseline. Original core, backend, PDFs, credentials, and indexed contents remain unchanged.

## Scope

Implemented the primary React application through all four internal gates:

| Gate | Result |
|---|---|
| A — API integration and application state | PASS; typed public contracts, fetch client, source/result state; lint/build passed |
| B — Functional Sources, Chat, Studio | PASS; all components compiled; live health, documents and OpenAPI checked before styling |
| C — Notebook-inspired layout | PASS; three desktop panels, restrained styles, stacked narrow layout; lint/build passed |
| D — Browser regression and report | PASS; real generation, downloads, isolated ingestion, security and integrity checks |

No dependency additions, database, model/configuration changes, Gradio removal, commit or push. Phase 11 has not started. This is the only permanent Phase 10 report; browser harnesses, counters, downloads, screenshots and snapshots stayed under `/tmp`.

## Final Architecture

```text
Browser
  → React + TypeScript + Vite
  → browser fetch / HTTP / multipart / Markdown Blob
  → existing FastAPI public endpoints
  → existing Python RAG core
  → Qdrant + filesystem + Gemini
```

React owns source selection, generated results and learning interactions. Credentials and generation remain server-side. Normal launch still uses `./scripts/dev_backend.sh` and `./scripts/dev_frontend.sh` from `project/`. The backend script runs one serving worker with a reload supervisor; no second serving worker or Gradio process was started.

## Core Protection

Before implementation, captured SHA-256 hashes for **43 protected files** in `src/` including prompts, `backend/`, `static/`, existing `data/` PDFs, `app.py`, `requirements.txt`, and `.env`. All match after verification. Generated caches were excluded.

No backend defect required a patch. Backend changes: **NONE**. Original Qdrant content was checked separately after server shutdown: **132 points**, with all IDs, payloads and vectors identical to the initial snapshot.

The real ingestion test used an ordinary filesystem copy of the closed Qdrant baseline, with existing supported environment overrides for temporary storage/data directories. It did not change `.env`, Gemini configuration, collection name, embedding model or core code.

## Frontend Structure

```text
frontend/
├── index.html
├── README.md
└── src/
    ├── App.tsx
    ├── main.tsx
    ├── useNotebook.ts
    ├── api/client.ts
    ├── types/
    │   ├── api.ts
    │   └── citations.ts
    ├── components/
    │   ├── AppHeader.tsx
    │   ├── Status.tsx
    │   ├── CitationList.tsx
    │   └── ExportButton.tsx
    ├── features/
    │   ├── sources/SourcesPanel.tsx
    │   ├── chat/ChatPanel.tsx
    │   └── studio/
    │       ├── StudioPanel.tsx
    │       ├── SummaryView.tsx
    │       ├── QuizView.tsx
    │       └── FlashcardsView.tsx
    └── styles/index.css
```

Plain React hooks manage application state; no state library or Axios was added. Existing dependencies, package manifests and lockfile were preserved. Existing README launch/use instructions were corrected to describe the functional frontend.

## API Integration

Types mirror `backend/schemas/api.py` and the inspected live OpenAPI schemas. Requests carry explicit filenames and supported page filters. Chat uses `k=6`; learning sends a nullable topic and otherwise leaves the backend retrieval defaults intact. No-topic generation therefore uses all selected matching chunks.

| Feature | Endpoint | Result |
|---|---|---|
| Health | `GET /api/health` | PASS; HTTP 200 |
| Documents | `GET /api/documents` | PASS; initial 3 indexed PDFs / 132 chunks; refresh works |
| Upload | `POST /api/documents/upload` | PASS; one real multipart ingestion in isolated storage, HTTP 200 |
| Chat | `POST /api/chat` | PASS; exactly one real generation, HTTP 200 |
| Summary | `POST /api/summary` | PASS; exactly one real generation, HTTP 200 |
| Quiz | `POST /api/quiz` | PASS; exactly one real generation, 3 items, HTTP 200 |
| Flashcards | `POST /api/flashcards` | PASS; exactly one real generation, 3 cards, HTTP 200 |
| Export | `POST /api/export` | PASS; all four result types, HTTP 200; actual browser downloads |

The shared client handles HTTP 400, 404, 422, 500 and network failure with concise Vietnamese messages. It translates status/allowlisted contract details rather than rendering arbitrary backend exception or validation text. Browser-local failure injections exercised those paths; they did not send additional real generation requests.

## Sources Panel

- Loads indexed documents automatically, with loading/error states and a document count.
- Starts with **zero selected sources**. Checkbox multi-selection, Chọn tất cả and Bỏ chọn work.
- Rows show filename, page count and chunk count. Long names truncate and retain their full filename in a tooltip.
- Refresh preserves valid selections and resets the page filter.
- The page selector uses actual indexed page metadata and is enabled only for exactly one PDF. Changing source selection resets it; selecting a second source disables it.
- Native PDF picker shows the selected filename. Empty/non-PDF/oversized files are rejected locally; upload is disabled while running. Successful upload reports indexed chunks and refreshes the list.
- Existing selections remain after upload. New sources are available for explicit selection; they are not automatically selected.

Browser checks confirmed that generation with no selected source shows **Vui lòng chọn ít nhất một tài liệu.** and sends no generation request.

## Chat

The central panel presents a conversation with a composer at the bottom. Gửi and Enter submit; Shift+Enter inserts a newline, and composition input is respected. The request captures current source/page selection and uses the validated default `k=6`.

Empty questions show **Vui lòng nhập câu hỏi.** without a request. During generation the pending question and **Đang tạo câu trả lời...** appear, and Send is disabled. A successful result appends to the conversation and clears the composer. A failed request preserves earlier conversation and the draft.

Exactly one real request asked the instructed question against:

`4 Complexity analyses show two distinct types of nonlinear dynamics in short heart period variability recordings.pdf`

> How many distinct types of nonlinear dynamics did the complexity analyses show in short heart period variability recordings?

Observed result: **HTTP 200**, approximately **8.34 seconds**, **6 citations**, and an answer stating **hai loại** with `[S2]`. Inline markers remained intact. Citation rows stayed compact; expanding one displayed source text. Chat Markdown export passed.

## Studio

Only the active tool is visible. Switching tools retains each generated result and its inputs. Existing results remain visible if a subsequent request fails. Loading disables the relevant generation action rather than the entire application.

### Summary

Optional topic and Tạo tóm tắt controls. Real no-topic generation over the selected PDF's 35 chunks returned HTTP 200 in approximately **12.89 seconds**, non-empty prose, **8 key points**, and **35 citations**. Sources remain collapsed by default. Summary survived a switch to Quiz and back, and a simulated failed regeneration. Markdown download passed.

### Quiz

Defaults to three questions; HTML form validation enforces integer counts from 1 to 50. Optional topic supported. The single real request returned **3 questions**, four options per question, and 35 response citations in approximately **3.42 seconds**.

One question appears at a time. Correct answer, explanation and item citations stay hidden until Kiểm tra đáp án. Both correct and incorrect feedback were checked. Navigation resets answer selection and reveal; first/last boundaries are disabled. Invalid counts `0`, `51`, `2.5` and blank were blocked without generation. Quiz remains available after switching Studio tools. Markdown download passed.

### Flashcards

Defaults to three cards; count range is 1–100 with an optional topic. The single real request returned **3 cards** and 35 response citations in approximately **2.87 seconds**.

One front appears at a time. Hiển thị đáp án locally reveals the back, optional hint and matching current-card citations. Navigation resets reveal; boundaries are disabled. Cards remain available after switching Studio tools. Markdown download passed.

## Local Interaction State

| Interaction | State behavior | Additional generation calls |
|---|---|---:|
| Quiz Check | Reveals correctness, answer and explanation | 0 |
| Quiz Previous/Next | Changes item; resets option and reveal | 0 |
| Flashcard reveal | Reveals back, hint and citations | 0 |
| Flashcard Previous/Next | Changes card; resets reveal | 0 |
| Studio switching | Keeps generated results and tool state | 0 |

Successful replacement of a quiz/card result mounts fresh interaction state. Failure does not replace a working result. Persistence is intentionally limited to the current mounted browser session; reload resets React state.

## Citation UX

One reusable `CitationList` renders filename/page rows and keyboard-usable native disclosures. Chat shows compact reference rows immediately; Studio groups sources under a collapsed count disclosure. Full source text is always inside a closed per-citation disclosure until expanded.

Quiz/card markers select matching response citations; brackets are normalized for matching without rewriting assistant answer markers. Section and secondary chunk ID are shown only inside expanded details. No filesystem paths, vectors or prominent document IDs are rendered.

## Export UX

Tải Markdown appears only for existing results and submits the corresponding validated JSON result to `/api/export`. The client reads `Content-Disposition`, receives a Blob, creates a temporary download link and releases the object URL. No server output path or persistence is requested.

| Browser-saved file | Bytes | Result |
|---|---:|---|
| `chat.md` | 10,757 | PASS |
| `summary.md` | 58,702 | PASS |
| `quiz.md` | 67,882 | PASS |
| `flashcards.md` | 72,941 | PASS |

Eight real export requests returned HTTP 200: four initial HTTP/Blob checks, followed by four successful saved-file checks after correcting the temporary CDP harness to keep Chrome's download behavior active during each session. No application export change was required. An additional browser-local simulated export failure verified the safe error message. Exports caused **zero Gemini calls**.

## Visual Design

An original Sources | Chat | Studio research workflow with a quiet light background, distinct white panels, subtle borders, restrained blue accent, system fonts and compact controls. Chat receives the largest desktop region. Sources use compact rows; Studio presents one active tool and internally scrollable results.

The neutral header reads Research Notebook with a short Vietnamese subtitle. There are no Google, NotebookLM, Gemini or AIVN assets/branding, promotional links, external fonts, decorative animations or elaborate effects.

Labels, button text, disabled controls, visible focus, radios, checkboxes and native disclosures provide basic keyboard accessibility. This was a functional accessibility check, not a full WCAG audit.

## Responsive Verification

| Resolution | Layout | Horizontal Scroll | Status |
|---|---|---|---|
| 1366×768 | Three columns; central Chat widest | None, page or visible panels | PASS |
| 1440×900 | Three columns; central Chat widest | None, page or visible panels | PASS |
| 1920×1080 | Three columns; flexible central Chat | None, page or visible panels | PASS |
| 860×900 | Stacked Sources → Chat → Studio | None, page or visible panels | PASS |

At intermediate widths Studio moves below Sources/Chat; at 900px and below all panels stack. Upload/composer/Studio controls remain accessible through normal page/panel scrolling. Long-name grid overflow found during screenshot inspection was fixed and retested. Screenshots were temporary and were not added to `reports/`.

## Browser Runtime Tests

Used installed headless Chrome with a dedicated temporary profile and a temporary Python CDP harness against `http://127.0.0.1:5173`. The backend ran at `http://127.0.0.1:8000`.

Verified initial header/panels, actual indexed documents, explicit empty selection, selection/clear/all/refresh, page-filter reset, empty-input blocking, Enter/Shift+Enter, real Chat/Summary/Quiz/Flashcards, disclosure behavior, local learning controls, result retention, four actual downloads, one real upload, and responsive layouts.

Supplemental browser-local injected HTTP 400/404/422/500 and network failures verified sanitized errors and conversation retention; a simulated Summary failure preserved its earlier result. These checks were separated from real request accounting. No React errors or unhandled promise rejections were recorded, and styles/documents loaded after the final clean reload. Chrome's own background registration/GPU notices were unrelated to the application.

FastAPI, Vite and the dedicated Chrome instance were stopped orderly. Test ports **8000, 5173 and 9222** were confirmed released. No unrelated process was stopped.

## API Call Audit

Browser fetch logging recorded real generation requests. Temporary server-side forwarding instrumentation counted actual `generate_content` invocations and Gemini HTTP sends by endpoint, without changing core/backend files or substituting provider output.

| Action | Real generation API requests | Gemini calls / HTTP sends |
|---|---:|---:|
| Chat | 1 | 1 / 1 |
| Summary | 1 | 5 / 5: four map batches + one reduce |
| Quiz | 1 | 1 / 1 |
| Flashcards | 1 | 1 / 1 |
| Quiz Check | 0 | 0 / 0 |
| Quiz navigation | 0 | 0 / 0 |
| Flashcard reveal | 0 | 0 / 0 |
| Flashcard navigation | 0 | 0 / 0 |
| Export, metadata, upload | 0 | 0 / 0 |
| **Total generation** | **4** | **8 / 8** |

All eight Gemini HTTP responses were 200. No extra generation request, provider failure or retry was observed. Upload uses the existing local embedding model; no Gemini generation occurred during indexing.

## Upload Integration

**PASS — real ingestion against isolated storage.** Exactly one multipart upload through React used the existing, previously unindexed file:

`5 Recurrence quantification analysis across sleep stages.pdf`

This is an existing research PDF, not fabricated test content or a duplicate of an indexed source. It contains 10 pages and was accepted by the actual core parser/indexer. The FastAPI response was HTTP 200 with **47 chunks indexed**. The UI displayed success, automatically refreshed to four sources, preserved its prior selection and allowed selecting the new source.

The backend used supported temporary overrides:

```text
RAG_STORAGE_DIR=/tmp/phase10_runtime/qdrant
RAG_DATA_DIR=/tmp/phase10_runtime/data
```

| Storage | Before | After | Impact |
|---|---:|---:|---|
| Original `storage/qdrant` | 132 points / 3 PDFs | 132 points / 3 PDFs | NONE; complete point/payload/vector equality |
| Isolated temporary copy | 132 points / 3 PDFs | 179 points / 4 PDFs | +47 points for the uploaded PDF |

After shutdown, the isolated copy's original 132 points also matched the initial baseline exactly. No manual Qdrant cleanup/deletion occurred. The uploaded copy remains temporary; it will not appear in the normal application's unchanged original collection. Existing PDFs in `data/` were not overwritten.

## Frontend Build / Lint

`npm run lint` and `npm run build` passed at Gates A, B and C and again after final code changes. Final frontend lint has no code warnings/errors; TypeScript and Vite production build pass. `git diff --check` also passed. No package manifest, lockfile or dependency change was needed.

The final CSS is linked from `index.html`, preserving the production bundle and development layout while avoiding Vite's absolute-source-path style attribute in representative browser HTML.

## Security

Non-disclosing scans covered **26 frontend source/build/HTML files**, including representative rendered HTML, real browser API payloads and all four saved Markdown files. The configured Gemini key was read only for an in-memory equality scan and never printed.

Checks passed for the configured credential, `GEMINI_API_KEY`, absolute workspace/runtime paths, tracebacks and private `vector`, `vectors`, `metadata` or `chunks` response fields. No `.env` contents were copied into the frontend. Safe failure tests verified that raw backend-like error text and private paths were not rendered.

Only intentional public citation source text is included. No key input, provider setting, Qdrant details, vectors or server filesystem controls were added to the UI. Development bundler tooling is not a production deployment/security boundary; this phase verified the stated source/build/HTML/API artifacts.

## Core Diff Audit

The following diff checks were empty:

```text
git diff -- src/
git diff -- app.py
git diff -- requirements.txt
git diff -- static/
git diff -- backend/
```

The protected hash snapshot independently confirms zero Phase 10 changes to those areas, prompts, `.env` and existing PDFs. Original Qdrant content equality was verified after orderly shutdown. There was no commit or push.

## Files Added / Modified

Modified existing frontend files:

- `frontend/README.md`: current launch/workflow instructions.
- `frontend/index.html`: Vietnamese language and linked stylesheet.
- `frontend/src/main.tsx`: stylesheet now linked through HTML.
- `frontend/src/App.tsx`: composed three-panel application.
- `frontend/src/types/api.ts`: public transport contracts.
- `frontend/src/api/client.ts`: typed fetch operations, safe errors and Blob downloads.
- `frontend/src/styles/index.css`: desktop/narrow productivity layout and controls.

Added frontend files:

- `frontend/src/useNotebook.ts`: source/request/generated-result state and operations.
- `frontend/src/types/citations.ts`: current-item citation matching.
- `frontend/src/components/AppHeader.tsx`, `Status.tsx`, `CitationList.tsx`, `ExportButton.tsx`.
- `frontend/src/features/sources/SourcesPanel.tsx`.
- `frontend/src/features/chat/ChatPanel.tsx`.
- `frontend/src/features/studio/StudioPanel.tsx`, `SummaryView.tsx`, `QuizView.tsx`, `FlashcardsView.tsx`.

Added permanent report: **this file only**.

## Known Issues

No BLOCKER, MAJOR, MINOR or COSMETIC application defect remains from the performed checks. Generated factual correctness was checked for the instructed Chat question; this is not a claim of universal generation accuracy. Tiny mobile layouts and a comprehensive accessibility audit remain outside the requested scope.

## Final Result

**PASS**. React and documents load; explicit source selection works; all four real generation features and exports work; local interactions do not regenerate; desktop and narrow layouts are usable; original core/backend/indexed baseline are unchanged; checked artifacts expose no credentials; lint/build pass; no BLOCKER or MAJOR defect remains.

Upload integration: **PASS in isolated temporary storage**, with **zero original Qdrant impact**.

Permanent Phase 10 report files created: **1**.

## Recommended Next Step

**PHASE 11 — FINAL FULL-SYSTEM REGRESSION AND FREEZE**.

Do not start Phase 11 in this task. No commit or push was performed.
