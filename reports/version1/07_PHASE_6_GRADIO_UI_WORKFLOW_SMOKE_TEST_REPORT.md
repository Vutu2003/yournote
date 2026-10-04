# Phase 6 — Gradio UI Workflow Smoke Test Report

Test date: 2026-09-30. Result: **PARTIAL PASS**.

## Test Scope

Tested the current Gradio application from the user workflow perspective. The application was opened in a real, local headless Chrome browser. Browser controls were operated through Chrome DevTools, and rendered DOM plus screenshots were inspected. This was automated browser interaction, not manual human GUI use. The Markdown file URL was also checked with HTTP. One existing unindexed PDF was uploaded; no source code was changed.

## Environment

| Item | Observed value |
|---|---|
| Working directory | `/home/vutu/Desktop/rag_notebooklm/project` |
| Python | 3.12.10, `project/.venv/bin/python` |
| Gradio | 6.13.0 |
| Launch command | `GRADIO_SERVER_NAME=127.0.0.1 .venv/bin/python app.py` |
| Local URL | `http://127.0.0.1:7860/` |
| Browser | Google Chrome 154.0.8037.92, local headless session |
| Gemini model | `gemini-flash-lite-latest` |
| Embedding model | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` |
| Qdrant | Local `storage/qdrant`, collection `rag_chunks` |
| Credentials | `.env` exists and Gemini key was detected; value was not printed or recorded |
| PDFs in `data/` | Five, numbered 1–5 |
| Indexed at start | PDF 4 only, 35 points |

## Current UI Structure

`app.py` builds a `gr.Blocks` page with AIVN branding and a Vietnamese usage note. The first row has a multi-PDF upload, “Nạp & Index” button and status area on the left; an existing-document selector, refresh button and single-document page filter on the right. The key input is a collapsed password accordion. Four tabs follow: Q&A with a chatbot and `k=6` by default; Summary with optional topic and `k=10`; Quiz with count 3 and `k=10`; Flashcards with count 15 and `k=16`. Each tab has a collapsed JSON debug area. Summary, Quiz and Flashcards have a Markdown file download component. Source entries are rendered in the output Markdown, with filename, page and chunk ID. The layout/style is defined in `static/style.css`.

Callback wiring: `_refresh_docs` refreshes the selector; `_pages_for_selection` updates the page list; `_upload_pdf` saves and indexes files; `_ask_chat` handles Q&A; `_summarize`, `_quiz` and `_flashcards` handle the three learning features. The learning buttons chain to `_write_export` for `exports/summary.md`, `exports/quiz.md` and `exports/flashcards.md` respectively. No standalone export button exists.

## Launch Test

**Startup PASS; browser load PASS.** Gradio bound to loopback at the URL above and Chrome rendered a nonblank page with the title, branding, upload, document area and four tabs. The initial screenshot showed no obvious clipped or overlapping primary controls at 1440 × 1000.

Terminal output contained nonfatal Starlette HTTP-422 deprecation warnings, an unauthenticated Hugging Face Hub warning during model load, a `google-genai` automatic-function-calling recommendation, and a local-Qdrant warning that payload indexes have no effect in embedded mode. No startup exception or callback traceback was observed. The Starlette warning alone does not establish a failed HTTP response.

## Document Workflow

The already indexed PDF, `4 Complexity analyses show two distinct types of nonlinear dynamics in short heart period variability recordings.pdf`, appeared after clicking **Làm mới danh sách tài liệu**. It was selected through the browser checkbox. The selector changed and the page filter became applicable. Selecting it did not index it again; the count remained 35 before the intentional upload.

**Upload tested: YES.** Chrome selected the existing, previously unindexed `2 Heart rate variability in normal and pathological sleep.pdf` (823,802 bytes) once. The upload component displayed its filename. Clicking **Nạp & Index** showed “✅ Đã nạp 1 file · 65 đoạn”; the selector refreshed to two documents and “100 đoạn văn”. After shutdown, Qdrant held 35 points for PDF 4 and 65 for PDF 2, total 100. No other PDF was indexed. Upload workflow: **PASS**.

## Q&A UI Test

Selected PDF: PDF 4. UI `k`: 6. Submitted question: “How many distinct types of nonlinear dynamics did the complexity analyses show in short heart period variability recordings?”

The chatbot displayed: “Các phép đo độ phức tạp đã chỉ ra sự hiện diện của hai loại động lực học phi tuyến tính khác nhau trong các chuỗi ghi nhận biến thiên khoảng thời gian tim [S2].” This materially answers **two**. A “Sources” section showed six entries, each with marker, filename, page and chunk ID; the cited S2 entry was on page 1. No browser alert or traceback appeared. The input cleared after completion. Q&A: **PASS**.

## Summary UI Test

With PDF 4 still selected and no topic, clicked **Tạo tóm tắt** once. The UI showed “Đang truy xuất ngữ cảnh… - 30.0%” during generation. It then rendered a Vietnamese prose summary, a “Key Points” list, a “Sources” section for all 35 chunks, and a `summary.md` file component. The output was approximately 10,336 visible characters; the generated Markdown was 58,909 bytes. The summary body itself did not show inline source markers; source entries followed it. No raw exception appeared. Summary: **PASS** for generation, with citation/readability concerns below.

## Quiz UI Test

Clicked **Tạo quiz** once at its default requested count of 3. The visible output said `Items: 3` and displayed three questions, four options per question, the answer, explanation, source markers, and source details. `quiz.md` was created (66,544 bytes). This is a static study sheet: the answer and explanation appear immediately; there is no answer-reveal interaction. Quiz: **PASS** for current implementation.

## Flashcards UI Test

Opened Advanced controls, changed **Số thẻ** from 15 to 3, verified both number input and slider showed 3, then clicked **Tạo flashcards** once. The output said `Cards: 3` and rendered three numbered cards with Front, Back, Hint and source markers. `flashcards.md` was created (67,259 bytes). Cards are presented as a long Markdown list; no flip or next-card control exists in this implementation. Flashcards: **PASS** for current implementation.

## Citation Presentation

| Feature | Marker visible | Filename visible | Page visible | Understandable |
|---|---|---|---|---|
| Q&A | Yes, inline `[S2]` and source list | Yes | Yes | Yes, six sources |
| Summary | Yes, in Sources list; no inline summary marker | Yes | Yes | Partly; 35 full entries overwhelm the summary |
| Quiz | Yes, in explanations/source entries | Yes | Yes | Partly; long source text interrupts questions |
| Flashcards | Yes, in card backs/source entries | Yes | Yes | Partly; long source text interrupts cards |

Chunk IDs are visible in all four source presentations. Core citations existed for all generated results. UI presentation is less usable for the learning features because full source content and all 35 corpus citations make the output long. These observations describe presentation; they do not independently verify factual grounding of every generated statement.

## Export Test

The Flashcards file component displayed `flashcards.md` and a download link. The chained callback wrote `exports/flashcards.md`. The displayed Gradio file URL returned HTTP 200 with 67,259 bytes identical to the export file, including three card headers. A programmatic browser click on the link did not produce a file in the isolated Chrome download directory, so an operating-system browser save was **not confirmed**. Export generation and serving: **PASS**; browser save confirmation: **NOT VERIFIED**.

## Raw JSON / Debug

The four tabs each have a collapsed “JSON debug” accordion. Opening the Flashcards panel after generation showed JSON with `scope`, `target` and `cards`, matching the three-card output; no Gemini key pattern was visible in the inspected panel. The API key input remained a password field. After the safe empty-question check, Q&A’s debug component displayed “Empty value”, because `_ask_chat` returned an empty raw value for the empty submission. Q&A JSON was not independently captured before that check. Recommendation for the next planning phase: retain debug data in a collapsed Advanced/Debug area and avoid clearing a valid previous result on an empty submission.

## Error Handling

One safe case was exercised: pressing Enter with an empty Q&A input after a successful answer. The previous answer remained, no exception appeared, and the input stayed empty. The UI gave no visible guidance that an empty question was ignored; its JSON debug value became empty. Classification: `ERROR_HANDLING` / `DEBUG_UI`, **MINOR**. No corrupted files, key removal or quota-error conditions were tested.

## UI/UX Findings

| Severity | Area | Finding | Evidence / impact |
|---|---|---|---|
| MAJOR | Document selection | Existing indexed documents are not populated on initial page load. | Initial browser view said “Chưa có tài liệu nào được index.” despite 35 points; clicking refresh populated PDF 4. A returning user may think re-upload is required. |
| MAJOR | Learning output/citations | Summary, Quiz and Flashcards render long source sections with full chunk text. | Summary showed 35 sources and 10,336 visible characters; Quiz/Flashcards also showed many source details. Reading the generated material requires substantial scrolling. |
| MINOR | Q&A empty input | Empty Enter silently does nothing and clears the Q&A debug value. | Browser error-handling check. |
| MINOR | Quiz | Correct answers are immediately visible. | Current Markdown rendering is readable as a worksheet, but there is no self-test reveal step. |
| MINOR | Flashcards | Front and Back appear together in a long list. | Three generated cards were readable, with no flip/navigation interaction. |
| COSMETIC | Language/labels | Vietnamese UI mixes English labels such as “Front”, “Back”, “Hint”, “Sources”, “Scope”, “Textbox” and “Code”. | Observed rendered Quiz/Flashcards/Q&A panels. |

No layout blocker was observed in the inspected 1440 × 1000 desktop view. Smaller responsive widths were not checked.

## Runtime Integrity

Qdrant `rag_chunks` count: **35 before → 100 after**. The 65-point increase matches the one intentional PDF 2 upload. Both expected document records remained; no collection recreation was observed. PDF 4 SHA-256 stayed `e126b46e0883ff2139927455ce342164b09509c9494556d573a99d4310eeb168`. PDF 2 SHA-256 after upload was `86ee086e3795a46e9fec3fbb3bbab0fe1beef5eb057f8666a1ee84c18d87af30`. Runtime output files were the three Markdown exports. No unexpected tracked source modification was found.

Gradio and isolated Chrome exited cleanly. Ports 7860 and 9222 were released; no test `python app.py` or test Chrome process remained.

## Result

**PARTIAL PASS.** Launch, actual browser Q&A, Summary, Quiz, Flashcards, document selection, and one new-PDF upload worked. Citation and learning-output presentation have the issues above. The Gradio file URL served the correct export, while a saved Chrome download was not independently confirmed.

## Source Changes

**NONE** to `app.py`, `src/`, `static/`, `requirements.txt` or `src/prompts/`. This phase added only this report and the intentional local Qdrant/export runtime data. `.gitignore` was already modified before Phase 6 and was not changed in this phase.

## Git Safety

`git status --short` after testing showed the pre-existing modified `.gitignore` and untracked `reports/`; `git diff --name-only` listed only `.gitignore`. `.env` and the API key were not printed or committed. No commit or push was performed.

## Recommended Next Step

**Phase 7 — UI/UX Improvement Plan**, without implementation: consolidate the confirmed findings, prioritize them, propose a clearer document-selection and learning-output flow, and identify the smallest necessary `app.py`/`static/style.css` changes while preserving the validated RAG core.
