# Phase 10.7 — Multi-Artifact Studio Report

## Phase Result

**PASS.** Each successful Studio generation now creates a separate artifact. Multiple Summaries, Quizzes and Flashcard decks coexist, with filename titles, independent viewers/progress and correct exports. The requested browser workflows, responsive checks, lint/build and protected-area audits passed.

## Scope

Frontend-only final UI improvement under `frontend/src/`, plus this single report. The Sources | Chat | Studio layout and existing generation/export contracts remain intact. No dependencies, state libraries, database, backend persistence, localStorage, deletion controls or artifact count limits were added.

Browser harnesses, provider counters, snapshots, screenshots and downloaded Markdown files stayed under `/tmp`. No upload, reindex, commit or push occurred. Deployment preparation and subsequent phases were not started.

## State Model

`useNotebook` now owns three initially empty collections:

- `summaryArtifacts: SummaryArtifact[]` wraps `SummaryResponse`.
- `quizArtifacts: QuizArtifact[]` wraps `QuizResponse`.
- `flashcardArtifacts: FlashcardArtifact[]` wraps `FlashcardsResponse`.

The frontend-only aliases use `StudioArtifact<T>`; public API response types are unchanged. On success, an artifact is created once and prepended with a functional state update. Earlier objects and IDs remain intact. Failure adds nothing and preserves all existing results and viewer progress.

The former latest-result and numeric revision states were removed. Artifacts live in the existing notebook hook; switching sources or Studio tabs does not replace these collections.

## Artifact Metadata

| Field | Meaning |
|---|---|
| `id` | Frontend-local `crypto.randomUUID()`, created after success |
| `title` | Deterministic title from the request's filenames |
| `createdAt` | Successful artifact creation time from `Date.now()` |
| `sourceFilenames` | Copied filenames selected when sending the request |
| `pages` | Copied page-filter snapshot, or an empty array |
| `topic` | Trimmed request topic, or `null` |
| `result` | Original typed API response used by viewer and export |

Request context is captured before awaiting generation. It is never reconstructed from the selection at completion. A live Summary test changed A to B while A was pending; A retained its own title and filenames. A frontend-only success fixture additionally changed filename selection, page filter and topic during the request and verified the complete original snapshot in React state.

Cards show source count, a full source-filename tooltip, and `HH:mm` in `Asia/Ho_Chi_Minh`. The timestamp tooltip includes the full date/time. IDs remain internal and are not displayed as user-facing labels.

## Title Strategy

Single PDF: remove the trailing `.pdf`, case-insensitively, without changing the source filename.

Multiple PDFs: use the first filename without extension followed by ` +{remaining count}`. Three selected documents therefore produce a title ending in ` +2`. This was verified with a frontend-only success fixture; uppercase `.PDF` removal was also checked directly.

Topic stays secondary as `Chủ đề: …`. Titles and topics occupy at most two visible lines; the complete strings remain available through tooltips, and the artifact title is also the card's accessible label. The selected viewer header shows the same filename title. No Gemini title-generation request exists.

## Summary Artifacts

Generation controls are followed by **Kết quả đã tạo** and a vertical newest-first card list. Each card shows its title, optional topic, key-point/citation counts, timestamp, **Xem nội dung** and the existing **Tải Markdown** action.

The live run created Summary A with 9 key points/35 citations, Summary B with 9/65, and another Summary B with a topic and 7/12. All three coexist. Generating another result does not automatically open a viewer.

Each Summary retains its own logical page: complete prose, key points, or citations. A's page remained unchanged after viewing B and after source/tab changes. The empty state is **Chưa có bản tóm tắt nào.**

## Quiz Artifacts

Two live generations created independent three-question Quiz artifacts, newest first, with filename titles and **Bắt đầu Quiz** / Markdown actions.

Each ID-keyed `QuizView` owns its current question, selected option and checked state. Answer selection/checking in B did not change A's selected radio or feedback; returning to either restored its current state. Each viewer uses a distinct `useId()` radio-group name to prevent native browser radio groups from interfering across mounted viewers.

Question navigation remains local and resets that question's selection/check state, preserving the prior interaction policy. There is no scoring/history system. The empty state is **Chưa có Quiz nào.**

## Flashcard Artifacts

Two live generations created independent three-card decks, newest first, with filename titles and **Xem Flashcards** / Markdown actions.

Each ID-keyed `FlashcardsView` owns its current card and reveal state. A and B retained different indices/reveal states across switching and close/reopen. Moving between cards resets reveal locally. The empty state is **Chưa có bộ Flashcards nào.**

## Viewer Integration

Studio selects a viewer through `{ type, artifactId }`, without copying the selected result into another state object. Each collection maps stable artifact IDs to its existing viewer and corresponding result; only the matching ID/type opens.

Viewers remain mounted with hidden portal overlays, so local progress belongs to that artifact for the mounted session. Adding a new artifact mounts a new viewer at its initial page/item and leaves older viewers intact.

Existing modal behavior passed for all three tools: close button, Escape, backdrop, focus restoration, background inert/scroll lock, Tab/Shift+Tab trapping, interior clicks, navigation boundaries, citation disclosures and reduced-motion behavior. Only one viewer is open at a time.

## Export Mapping

Each card passes its own `artifact.result` to the unchanged `ExportButton`. Each viewer footer likewise exports the result belonging to its ID-keyed viewer. API client, export schema, serialization and backend download naming were not changed.

All six A/B artifacts were downloaded through the actual browser. Export requests were compared with their exact original responses, and downloaded files were compared with the returned Markdown. Each A/B pair differed as expected.

| Artifact | Download size |
|---|---:|
| Summary A | 59,227 bytes |
| Summary B | 108,502 bytes |
| Quiz A | 70,148 bytes |
| Quiz B | 111,028 bytes |
| Flashcards A | 70,973 bytes |
| Flashcards B | 111,029 bytes |

Three additional exports of older A artifacts, after selecting the third PDF, still sent the exact correct results. There were nine real export requests total, all HTTP 200, with zero Gemini calls. Temporary audit copies were renamed under `/tmp` solely to compare downloads; application download behavior remains unchanged.

## State Preservation

Repeated single-source, multi-source and empty-source selections, and repeated Summary → Quiz → Flashcards → Summary switches, preserved every card's ID, title, sources, topic and creation time.

Viewer close/open and switching between older/newer artifacts preserved independent progress. Simulated HTTP 500 generation failures for all three tools preserved cards and progress, displayed existing safe errors/toasts, and made no backend/provider request. Raw injected error text/private paths were not displayed.

Stable card keys preserve the existing completion effect: animation logging observed exactly one `result-ready` start per created artifact, including each of the three fixtures. Earlier cards did not replay on later generation or switching. Success toasts remained present, with at most three simultaneous toasts observed.

## Duplicate Generation

Regenerating Summary B with topic **Phương pháp nghiên cứu** created a distinct UUID and a third Summary card above the previous B result. Both B artifacts retain the same deterministic filename title. Secondary topic, creation time and order distinguish them; neither earlier A nor B was overwritten.

The duplicate-generation regression reused this completed request for follow-up checks; no fourth live Summary request was made.

## Session Persistence Policy

All artifacts and interaction progress remain in React memory for the mounted browser session. Source changes, tool switches and viewer close/open preserve them. Browser refresh resets artifacts, viewers, progress, Chat and source selection; a fresh reload verified this with zero generation requests and a clean console.

There is no database, localStorage or backend session schema. Application restart starts a fresh browser session. No artifact cap or card-list pagination was introduced.

## Browser Regression

The installed headless Chrome used a dedicated temporary profile against `./scripts/start_all.sh`: React at `127.0.0.1:5173`, FastAPI at `127.0.0.1:8000`, without Gradio.

Existing indexed sources:

- **A:** `4 Complexity analyses show two distinct types of nonlinear dynamics in short heart period variability recordings.pdf` — 35 chunks.
- **B:** `2 Heart rate variability in normal and pathological sleep.pdf` — 65 chunks.

| Workflow | Result |
|---|---|
| Summary A/B | PASS: two live results coexist, B first, exact viewer text/key points and exports |
| Quiz A/B | PASS: two three-question results, independent selection/check/index, correct exports |
| Flashcards A/B | PASS: two three-card decks, independent index/reveal, correct exports |
| Same-source regeneration | PASS: third live Summary added, previous results retained |
| Studio switching | PASS: all collections/metadata persist; zero generation calls |
| Viewer | PASS: ID mapping, retained progress, modal/keyboard/citation behavior and local navigation |
| Export | PASS: six distinct A/B downloads plus three older-artifact retests; exact payload/file checks |
| Chat regression | PASS: one live request, history/citations, exact clipboard answer, copy feedback/toast |

Three frontend-only success fixtures reused existing responses to test page/topic snapshot changes, a three-source title and six-card layout. They were separately marked in the temporary request audit and sent no request to FastAPI or Gemini. Frontend-only failure injection was likewise separate from live calls. No fixture code was added to the application.

Temporary harness corrections addressed hidden-tab text formatting, selecting the correct visible tab before viewport measurements, and attaching the reload logger to an enabled browser Page domain. Checks were completed using existing results. The final interaction and fresh-reload audits recorded no React console errors or unhandled rejections.

## API Call Audit

Browser request logging separated real calls from synthetic frontend responses. Temporary forwarding instrumentation outside the repository counted actual Gemini SDK invocations and HTTP sends by endpoint without modifying backend/core code or substituting live generated output.

| Action | Real generation requests | Gemini invocations / HTTP sends |
|---|---:|---:|
| Summary A | 1 | 5 / 5 |
| Summary B | 1 | 8 / 8 |
| Same-source Summary B with topic | 1 | 3 / 3 |
| Quiz A/B | 2 | 2 / 2 |
| Flashcards A/B | 2 | 2 / 2 |
| Chat | 1 | 1 / 1 |
| Viewer open/close/switch | 0 | 0 / 0 |
| Source/Studio switching | 0 | 0 / 0 |
| Summary pagination | 0 | 0 / 0 |
| Quiz check/navigation | 0 | 0 / 0 |
| Flashcard reveal/navigation | 0 | 0 / 0 |
| Copy, citations, toasts | 0 | 0 / 0 |
| Artifact export | 0 | 0 / 0 |
| Frontend success/failure fixtures | 0 | 0 / 0 |
| **Total live generation** | **8** | **21 / 21** |

Summary uses the unchanged core map/reduce strategy: A requires four maps plus reduce; B requires seven maps plus reduce; the topic-filtered B result uses two maps plus reduce for 12 chunks. These provider counts are internal work for the three explicit Summary actions, not additional frontend generations. All 21 provider HTTP responses were 200, with matching successful completions and no observed retry.

All eight live generation requests and nine exports returned HTTP 200. Initial document-list logging included React StrictMode's mount requests; fresh reload only fetched documents. No upload/indexing request occurred.

## Responsive Check

Six Summary cards were used: the three live results plus three marked frontend-only fixtures. All three viewer types were checked at every requested resolution. Screenshots remained under `/tmp` and were visually inspected.

| Resolution | Studio viewport / content height | Cards/titles | Viewers/footer | Horizontal overflow |
|---|---|---|---|---|
| 1366×768 | 549 / 1462 px | PASS | PASS | None |
| 1440×900 | 681 / 1462 px | PASS | PASS | None |
| 1920×1080 | 861 / 1462 px | PASS | PASS | None |
| 860×900 | 760 / 1380 px | PASS | PASS | None |

The Studio body scrolls internally to its oldest card. Full filename tooltips remain available; title height stays within two lines. Cards fit the panel, and every viewer and footer remains within the viewport. The existing stacked layout is retained at 860 px.

## Build / Lint

**PASS:** `npm run lint`, `npm run build` and `git diff --check`. TypeScript and the production Vite build completed successfully. No application lint warnings/errors, weakened types or dependency changes were introduced.

## Backend/Core Integrity

- **Backend: unchanged.**
- **Core `src/`, including prompts: unchanged.**
- **Qdrant: unchanged**, with 132 point IDs, payloads and vectors equal to the pre-phase snapshot.
- **Gemini and Qdrant configuration: unchanged.**

SHA-256 comparisons confirmed all **73 protected baseline files** unchanged, including backend/core, indexed PDFs, `.env`, `app.py`, `static/`, requirements, runtime scripts, prior reports, API client/types, frontend entry HTML, README and package/lockfile. Required protected-area Git diffs exactly matched their pre-phase baseline, preserving prior work.

Non-disclosing scans covered **39 source/build/HTML/artifact/download files**, real request/response structures and the seven allowed artifact wrapper fields. No configured credential, `GEMINI_API_KEY`, absolute workspace/backend path, traceback, vector/embedding structure or private metadata was exposed in the checked outputs. The key was compared in memory and never printed. Public generated results and citations retain their existing API fields.

After testing, `./scripts/stop_all.sh` stopped the project-owned FastAPI/Vite runtime. The dedicated Chrome instance was closed; ports **8000, 5173 and 9224** were verified released. Unrelated processes were not stopped.

## Files Changed

Frontend changes relative to the Phase 10.7 baseline:

- Added `frontend/src/types/artifacts.ts`: typed frontend wrappers, copied request context, UUIDs and deterministic titles.
- Modified `frontend/src/useNotebook.ts`: three newest-first artifact collections and success-only additions.
- Modified `frontend/src/features/studio/StudioPanel.tsx`: per-tool lists, compact empty states and active artifact ID/type.
- Modified `frontend/src/components/ResultCard.tsx`: filename/topic/source/time metadata with existing viewer/export actions and completion feedback.
- Modified `frontend/src/components/ResultViewerModal.tsx`: selected artifact title in the viewer header.
- Modified `frontend/src/features/studio/SummaryView.tsx`: receive the artifact title while retaining local pagination.
- Modified `frontend/src/features/studio/QuizView.tsx`: receive the title and use isolated radio-group names.
- Modified `frontend/src/features/studio/FlashcardsView.tsx`: receive the title while retaining local interaction state.
- Modified `frontend/src/styles/index.css`: vertical artifact lists, compact metadata and two-line title/topic truncation.

Exactly one permanent report was added: `reports/version2/PHASE_10_7_MULTI_ARTIFACT_STUDIO_REPORT.md`. Chat, export transport, API schemas, HTML, README, dependency files, runtime scripts, backend and core were not modified in this phase.

## Known Issues

No unresolved **BLOCKER**, **MAJOR**, **MINOR** or **COSMETIC** issue was observed in the performed checks. Session reset on refresh is the requested persistence policy. Accessibility checks were functional browser checks, not full certification.

## Final Result

**PASS** for multiple Summary/Quiz/Flashcard artifacts, newest-first ordering, filename titles, ID-specific viewers and exports, duplicate generation, preserved collections/progress, failure retention, finite new-card feedback, zero extra generation from local interactions, responsive layouts, clean build/lint and unchanged backend/core/Qdrant.

**FINAL UI IMPROVEMENT COMPLETE.** No commit or push. Runtime stopped.

## Next

Deployment preparation → deployment test → final freeze → documentation.

Subsequent work covers Hugging Face/production preparation, deployment smoke testing, final regression/freeze, and README/final report/diagrams/presentation. These tasks were not started in this phase.
