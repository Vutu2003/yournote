# NotebookLM-Inspired UI Version 2 Plan

Plan date: 2026-09-30. **Planning only; no Version 2 implementation in this phase.** Proposed product name: **Research Notebook**. This is an original Gradio interface for studying uploaded PDFs. The left/center/right organization draws on the documented Sources/Chat/Studio interaction model, not on Google branding, assets, or a pixel copy. [Google's description of the three areas](https://blog.google/innovation-and-ai/models-and-research/google-labs/notebooklm-new-features-december-2024/).

## Goal

Give the validated RAG application a focused document workspace: **Nguồn tài liệu | Trò chuyện | Studio**. Indexed documents should be visible on load; Q&A should be the center task; generated study material should be readable and interactive; citations should be compact until expanded. Keep Gradio and the existing RAG/learning functions. Treat the browser UI as the only target of this plan, with zero changes to backend modules, models, prompts, dependencies, or stored vectors.

## Validated Backend Baseline

- [Phase 4](05_PHASE_4_RAG_END_TO_END_SMOKE_TEST_REPORT.md) passed PDF retrieval, Gemini Q&A, source-marker construction, and a grounded answer. `src.rag.answer()` already returns `RagAnswer` with answer, citations, and chunks.
- [Phase 5](06_PHASE_5_LEARNING_FEATURES_SMOKE_TEST_REPORT.md) passed Summary, Quiz and Flashcards against the indexed PDF. `Summary`, `QuizSet` and `FlashcardSet` already carry the fields needed for a custom UI renderer. The no-query document path can include every selected chunk, which explains long citation lists and potentially several Summary calls.
- [Phase 6](07_PHASE_6_GRADIO_UI_WORKFLOW_SMOKE_TEST_REPORT.md) exercised the real Gradio UI in local headless Chrome: launch, document selection, Q&A, Summary, Quiz, Flashcards and one PDF upload worked. It reported **PARTIAL PASS** because indexed documents required manual refresh and learning outputs were dominated by sources. After that intentional upload, the report recorded 100 Qdrant points across two PDFs. This is the Phase 6 observation, not a new Phase 7 measurement.
- The existing `src.export.export()` writes complete Markdown, including source text. V2 should render a separate compact **screen view** from the same returned model while preserving the current full Markdown as the download payload. This avoids backend/export changes.
- Installed Gradio is 6.13.0; local API inspection confirmed `Blocks.load`, `gr.State`, `gr.Radio`, `gr.Accordion` and `gr.Button` are available. Stateful Quiz/Flashcards are therefore feasible in `app.py`; event wiring and browser behavior still require Phase 8 verification.

## Current UI Audit

Current authority: `app.py` and `static/style.css`. The UI is a top branding/note area, a two-column upload/document area, then four full-width tabs. `app.py` calls core functions directly. The following dispositions are **plans**, not edits made now.

| Current element | Disposition | V2 reason / destination |
|---|---|---|
| AIVN logo, AIVN header, AIO2025 subtitle, VLAI/AI VIETNAM footer | REMOVE | Replace with neutral compact Research Notebook title; remove user-facing provider/course promotion. |
| Large warning-style usage note and separate long usage accordion | REMOVE / SIMPLIFY | Replace with short contextual empty states and actionable statuses; no welcome banner. |
| `gr.Blocks` and direct Python callbacks | KEEP | Retain current framework and tested core call paths. |
| Upload `gr.File`, “Nạp & Index” button, status | MOVE / SIMPLIFY | Put a compact “Thêm PDF” flow and short index status in Sources. |
| Indexed-document `CheckboxGroup` and multi-select | KEEP / MOVE | Primary list in Sources, with obvious selected count; keep filename identity. |
| Refresh button | KEEP / SIMPLIFY | Small secondary action; no longer required on first load. |
| Page dropdown | KEEP / MOVE | Show/enable for exactly one selected PDF; reset to all pages otherwise. |
| Gemini key password textbox | MOVE | Keep as optional runtime override under collapsed Nâng cao / Cài đặt; `.env` remains default. Never prefill from `.env`. |
| Configuration accordion with model/storage paths | HIDE | Developer/debug area only; omit raw filesystem paths from normal UI. |
| Q&A tab and chatbot | REDESIGN / MOVE | Persistent center Chat panel; retain `_ask_chat` → `answer()`. |
| Q&A `k` slider | MOVE | Collapsed Advanced control, default still 6 unless deliberately revised later. |
| Summary controls and output | REDESIGN / MOVE | Studio tool, compact summary/key points and collapsed source list. |
| Quiz controls/output | REDESIGN / MOVE | Studio tool with one question at a time and answer hidden until action. |
| Flashcards controls/output | REDESIGN / MOVE | Studio card viewer with reveal and Previous/Next. |
| Per-tab JSON debug accordions | MOVE / CONSOLIDATE | One clearly secondary Advanced/Debug area, collapsed by default. |
| Three `gr.File` Markdown downloads and `_write_export` | KEEP / MOVE | Keep one download for the current Studio result; preserve generated file content. |
| `src.export` source-heavy Markdown shown directly in normal UI | REDESIGN | Use UI-only compact renderers; keep canonical full export separately. |
| Current progress/status areas | KEEP / SIMPLIFY | Short Vietnamese actionable feedback in each relevant panel; technical warnings stay in terminal. |
| Current gradient, large shadows, external Inter import, 979-line CSS | REDESIGN | Restrained neutral tokens, system font stack, component classes and responsive panel sizing. |

The present `_refresh_docs()` returns document choices but runs only on Refresh/upload, so initial display falsely says there are no indexed documents. It also resets the selection to `[]`. `_ask_chat()` returns empty debug text for an empty question, clearing the previous debug result. `_run_feature()` passes the full `src.export` Markdown to Gradio, producing the long visible source sections. These are app-layer changes to plan; no core change is required.

## Elements to Remove

Remove from the **rendered UI** in Phase 8: `_img_b64` logo rendering, `static/aivn_logo.png` reference and `allowed_paths` entry if no longer needed, AIVN/AIO2025/VLAI/AI VIETNAM text and footer links, `_INFO_NOTE_HTML`, the verbose `_USAGE_MARKDOWN` block, the warning-colored intro card, redundant document-list prose, and promotional/decorative icon treatment. Do not delete `static/aivn_logo.png` during Phase 7. After V2 no longer references it, it is a candidate for Phase 8 cleanup. Technical dependency warnings may continue in terminal logs; normal UI should show only application status or safe error text. No global Python-warning suppression is proposed.

## NotebookLM-Inspired Design Principles

Use the **workflow hierarchy** of sources → source-grounded chat → study tools, as described in Google's own overview; keep the title, palette, styling, labels, and feature set original. [Google product overview](https://blog.google/innovation-and-ai/models-and-research/google-labs/notebooklm-new-features-december-2024/). Avoid Google/NotebookLM logos, trademarks in product branding, proprietary assets, and a pixel-perfect clone. The project offers PDF sources, Q&A, Summary, Quiz and Flashcards only; do not imply it has web discovery, audio, video, or Google account features.

Design each view around the next user action. Display selected filenames and a concise status first, put technical controls behind Nâng cao, and reveal detailed chunks only on request. Do not make a visually compact citation look like independent fact checking: marker presence and factual support remain different things.

## Target Information Architecture

Use one `gr.Blocks` shell and a primary `gr.Row` of three `gr.Column`s. Set stable `elem_classes` such as `sources-panel`, `chat-panel`, `studio-panel`; size and responsive behavior should be defined from these classes instead of Gradio-generated class names. The header is a single compact row with **Research Notebook** and a small **Nâng cao / Cài đặt** entry. Keep a narrow status strip near the affected panel rather than a global warning banner.

At wide desktop widths, allocate roughly 250–290 px to Sources, remaining flexible width with at least ~500 px to Chat, and 330–380 px to Studio. Avoid CSS `min-width` totals that exceed 1366 px. Let the chatbot and Studio results scroll inside their panels where practical; keep the chat input near the panel bottom. Studio shows tool choices plus **one** active result, not three long tab outputs at once.

## Sources Panel

- Show **Nguồn tài liệu**, compact **Thêm PDF** upload/index controls, `CheckboxGroup` of indexed filenames, selected count and a small Refresh action. No full local paths in normal output.
- **P0 auto-load:** register `demo.load(fn=_refresh_docs, inputs=[], outputs=[docs, doc_map_state, page, doc_summary, doc_list_md])`, or a tiny UI wrapper with equivalent outputs. It calls `list_documents()` only; it must not invoke ingestion or embedding. Initialize selection to none and communicate “Chọn ít nhất một tài liệu” for generation attempts without a selection.
- For manual Refresh/upload, adapt the UI helper to preserve still-valid explicit selections where possible; do not silently select an uploaded file. When exactly one source is selected, show its available pages. With zero or multiple sources, set page to “(Tất cả trang)” and disable it. Preserve existing `filenames` filtering through `_filters()`.
- Status examples: “Đã index 1 tài liệu.”, “Đã chọn 2 nguồn.”, “Không thể index PDF. Xem chi tiết trong Debug.” Do not surface local paths or raw traceback. Keep the existing upload callback and `save_and_ingest_pdf()` boundary.

## Chat Panel

Keep `gr.Chatbot`, a concise empty state, a textbox labelled **Hỏi tài liệu**, and a visible **Gửi** button; Enter should also submit. Both triggers should call the same UI handler. Put `k` in collapsed Nâng cao. Use the selected document/page controls as current `_filters()` does. Before calling `answer()`, reject empty questions and no-source selection with short feedback **without** clearing previous chat or debug state. Catch backend exceptions at the UI boundary, log details to terminal, and show a safe Vietnamese message in a dedicated status component. Preserve the `src.rag.answer()` path and default `k` unless Phase 8 testing proves a need to change it.

A sticky-ish composer can be approximated by a flex column with chatbot scroll area and input row at the bottom of `chat-panel`. Gradio's rendered DOM should be checked at target widths before relying on `position: sticky`; a normal bottom row inside a bounded panel is the safer fallback.

## Studio Panel

Show **Studio** with three compact choices: **Tóm tắt**, **Quiz**, **Flashcards**. A tool selection reveals only its relevant controls, current generated result and Markdown download. Keep topic and count where useful; put retrieval `k` in collapsed Nâng cao. Each Generate action uses the current explicit source/page selection and existing `_summarize`, `_quiz`, `_flashcards` core calls. Do not add new generation modes or new backend services. When generation completes, store the validated model data (or its `model_dump()` dict) in per-session `gr.State`, reset that tool's view index/reveal flag, render a compact screen view, and retain canonical full Markdown for export.

## Q&A Design

Render `RagAnswer.answer` with its inline `[S#]` markers unchanged. Beneath each assistant response, show a compact **Nguồn tham chiếu** section: `[S2] filename · tr. 1`, with chunk text and IDs inside a nested **Chi tiết** disclosure. Prefer referenced markers first; if the model answer contains none, show retrieved sources as “Nguồn đã truy xuất”, without implying each was cited by the answer. Escape filename, source text and generated prose appropriately when building HTML; do not inject raw untrusted text into `gr.HTML`. Keep the full `RagAnswer` in debug/canonical data for inspection.

## Summary Design

Normal view: title **Tóm tắt**, prose summary, **Ý chính** bullet list, then a collapsed **Nguồn tham chiếu (N)** section with compact marker/filename/page rows. `Summary` has citations for its input chunks but no per-sentence marker mapping; label the section “Nguồn đã sử dụng” rather than claiming a marker supports a particular sentence. A nested detail per row can expose full chunk text and chunk ID. The existing full `src.export.export(result, fmt="md")` remains the download payload. No change to `summarize()` or map/reduce behavior.

## Quiz Design

**App-only feasibility:** `QuizSet.items`, four `options`, `correct_index`, `explanation`, `source_markers`, and `citations` already provide everything needed. Use `gr.State` for current `QuizSet` data, current index and reveal/check state; `gr.Radio` for the selected option; `gr.Button` for **Kiểm tra đáp án**, **Câu trước**, **Câu tiếp theo**; `gr.Markdown`/safe HTML for prompt, feedback and compact citations. Generation initializes question 1 with no option chosen and no visible answer. Checking compares the selected option with `correct_index` and reveals correct/incorrect, the answer and explanation; navigating resets the radio/reveal state for the new question. Guard empty sets and boundaries. The planned UI never reveals an answer before action, including after navigation. If event/state synchronization proves brittle in Phase 8, fallback to one question at a time with **Hiển thị đáp án** and Previous/Next. Keep `generate_quiz()` and `QuizSet` untouched; export the complete set separately.

## Flashcards Design

**App-only feasibility:** `FlashcardSet.cards` already carries `front`, `back`, `hint`, `topic` and source markers. Use `gr.State` for set/index/reveal, one card display, **Hiển thị đáp án**, **Thẻ trước**, **Thẻ tiếp theo**. Show “Thẻ 1 / N” and front by default. Reveal displays back, optional hint and compact sources. Navigation resets reveal to hidden. Empty/boundary states should have safe disabled buttons or no-op feedback. Fallback if Gradio state/navigation proves unreliable: a single-card viewer with a reveal button and simple index selector. No schema or generation changes; full set remains downloadable.

## Citation Design

Two levels:

1. **Normal view:** only markers, filename and page. For Quiz/Flashcards, show the current item's `source_markers` resolved against the set's `citations`; do not list all corpus chunks below every item. For Summary, keep its entire source list inside one collapsed section because it has no item-level mapping.
2. **Details/Debug:** expanded chunk text, `chunk_id`, optional section, retrieval score where available, scope/target and raw JSON. Never make full chunks the default reading surface.

Preserve each `[S#]` mapping from the returned model. Rendering is presentation only; it neither rewrites core citations nor asserts that a cited source proves a generated claim. Retain HTML escaping and use concise Vietnamese labels. Existing `src.export` may stay verbose in downloaded Markdown; the on-screen renderer must no longer call its full text as the primary display.

## Advanced / Debug Design

Use one collapsed **Nâng cao / Debug** area, likely as a compact global accordion below the panels or in Settings. Put model/storage metadata, runtime Gemini key override, relevant `k` controls, and per-feature JSON inspection there. Because each feature has different data, use a selection control or conditionally visible JSON view instead of four prominent accordions. Keep JSON secondary and readable. Recommend **option B** for the key: preserve the password override in Advanced/Settings, keep the `.env` path as normal configuration, leave the textbox blank by default, and never echo the configured key to any component or log. This has lower regression risk than removing the current override path.

## Error and Status UX

| Situation | Normal UI text | Terminal / Debug behavior |
|---|---|---|
| Upload complete | “Đã index 1 tài liệu.” | Full callback log may remain. |
| No source selected | “Vui lòng chọn ít nhất một tài liệu.” | Do not invoke core generation. |
| Empty question | “Vui lòng nhập câu hỏi.” | Preserve previous chat/debug; no Gemini call. |
| No retrieved context | “Không tìm thấy đủ thông tin trong nguồn đã chọn.” | Preserve core's insufficient-context result in debug. |
| Generation exception | “Không thể tạo nội dung. Vui lòng thử lại.” | Log exception details in terminal; avoid raw traceback in normal panels. |

Hugging Face, Qdrant embedded-mode, google-genai and Starlette warnings observed in Phase 6 were terminal messages, not evidence that they were visible in the app. The V2 rule is to keep such technical messages out of normal UI, not to suppress Python warnings globally. UI wrappers should avoid showing raw exception strings that may contain paths, provider details or credentials.

## Language Plan

Primary interface language: Vietnamese. Use **Nguồn tài liệu**, **Thêm PDF**, **Tài liệu đã index**, **Trò chuyện**, **Hỏi tài liệu**, **Nguồn tham chiếu**, **Tóm tắt**, **Ý chính**, **Quiz**, **Flashcards**, **Kiểm tra đáp án**, **Hiển thị đáp án**, **Câu trước / Câu tiếp theo**, **Thẻ trước / Thẻ tiếp theo**, **Tải Markdown**, **Nâng cao / Debug**. In normal output, replace “Front/Back/Hint/Sources/Scope” with “Mặt trước/Mặt sau/Gợi ý/Nguồn tham chiếu/Phạm vi”. Keep RAG, PDF, JSON, Gemini, Qdrant and embedding as technical terms. Gradio's built-in “Textbox”/“Code” labels should be hidden or replaced through component labels where supported; raw schema keys can remain English inside Debug JSON.

## Visual Style

Use a neutral, original palette, for example: background `#f6f7f9`, panel `#ffffff`, primary text `#20242b`, secondary text `#626b78`, border `#e2e6eb`, one restrained blue accent `#435f9b`, success `#2f7655`, error `#a33b3b`. These are design proposals, not code. Favor 10–14 px radii, subtle separators and minimal shadows. Remove the current fixed multicolor gradient, bright button glow, large hero/logo treatment and external Google Fonts import. Use `system-ui`, Segoe UI/Arial fallbacks; no font download. Product title should fit a compact header, section headings be modest, body text ~14–16 px, and metadata smaller but still readable on a projector.

## Responsive Strategy

Target 1366×768, 1440×900 and 1920×1080 first. At 1366 px, all three panels should fit without horizontal page scrolling; verify actual Gradio `min_width`s and long filenames. At a narrower breakpoint around 1100–1200 px, allow Studio below Chat or stack the three panels while retaining source selection before question entry. At ≤860 px, stack **Sources → Chat → Studio**. Limit panel height to the viewport only where internal scrolling remains accessible; avoid clipping controls, citations or download links. Test browser rendering at the three desktop sizes and one stacked fallback in Phase 8/9. Phase 6 visually checked only 1440×1000; the other widths are future acceptance tests, not verified facts.

## Version 2 Wireframe

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ Research Notebook                                      Nâng cao / Cài đặt ▾ │
├────────────────────┬───────────────────────────────┬────────────────────────┤
│ NGUỒN TÀI LIỆU     │ TRÒ CHUYỆN                    │ STUDIO                 │
│ + Thêm PDF         │ Hỏi về các nguồn đã chọn      │ [Tóm tắt][Quiz][Thẻ]   │
│ Đã chọn: 1 nguồn   │                               │                        │
│ ☑ Paper 4.pdf      │ Bạn: ...                      │ Công cụ đang chọn      │
│ ☐ Paper 2.pdf      │ Trả lời ... [S2]              │ Thiết lập cần thiết    │
│ Trang: Tất cả  ▾   │ Nguồn tham chiếu ▸            │ [Tạo nội dung]         │
│ ↻ Làm mới          │                               │                        │
│ Trạng thái index   │                               │ Kết quả / card viewer  │
│                    │                               │ Nguồn tham chiếu ▸    │
│                    │ Hỏi tài liệu...       [Gửi]   │ [Tải Markdown]         │
├────────────────────┴───────────────────────────────┴────────────────────────┤
│ Nâng cao / Debug ▸                                                         │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Summary subview**

```text
STUDIO / TÓM TẮT
Chủ đề (tuỳ chọn) [...]           [Tạo tóm tắt]
Tóm tắt: đoạn văn ngắn theo dữ liệu trả về
Ý chính: • ... • ...
Nguồn đã sử dụng (35) ▸  [S1] Paper 4.pdf · tr. 1  [S2] ...
[Tải Markdown]
```

**Quiz subview**

```text
STUDIO / QUIZ        Số câu [3]       [Tạo quiz]
Câu 1 / 3: ...?
○ A ...   ○ B ...   ○ C ...   ○ D ...
[Kiểm tra đáp án]
Sau khi kiểm tra: Đúng/Sai · Đáp án đúng · Giải thích
Nguồn tham chiếu ▸
[Câu trước] [Câu tiếp theo]        [Tải Markdown]
```

**Flashcards subview**

```text
STUDIO / FLASHCARDS  Số thẻ [3]     [Tạo thẻ]
Thẻ 1 / 3
┌────────────────────────────┐
│ Mặt trước: câu hỏi/khái niệm│
└────────────────────────────┘
[Hiển thị đáp án]
Sau khi mở: Mặt sau · Gợi ý · Nguồn tham chiếu ▸
[Thẻ trước] [Thẻ tiếp theo]       [Tải Markdown]
```

## File-Level Change Map

| File / component | Implementation idea for Phase 8 | Risk | Backend impact |
|---|---|---|---|
| `app.py` header/footer, `_INFO_NOTE_HTML`, `_USAGE_MARKDOWN`, `_img_b64` | Replace with compact neutral title; remove branding, intro and footer UI references. | Low: inspect all asset references/allowed paths. | None. |
| `app.py` `gr.Blocks` tree | Rebuild placement as Sources/Chat/Studio columns; move existing components and events. | Medium: Gradio event inputs/outputs must remain aligned. | None. |
| `app.py` `_refresh_docs`, `demo.load`, selection events | Auto-populate on load; preserve valid explicit selections on later refresh; reset page filter appropriately. | Medium: per-session UI state and Qdrant read timing. | Read-only `list_documents()`; no indexing. |
| `app.py` `_upload_pdf` and status presentation | Keep indexing callback, shorten normal messages, log full failure details safely. | Medium: mixed multi-file success/failure feedback. | Same `save_and_ingest_pdf()` call. |
| `app.py` `_ask_chat`, `_ask` and new compact render helper | Validate inputs, add Send event, format answer/citations without full source dump in primary view. | Medium: preserve markers, escaping and chatbot history. | Same `answer()` call and filters. |
| `app.py` `_run_feature`, feature wrappers and UI state | Return model data to screen renderer plus canonical Markdown for export; handle safe errors. | Medium: callback output/state contracts. | Same `summarize()`/`generate_*()` calls. |
| `app.py` Quiz viewer handlers | Store set/index/reveal, Radio, check, Previous/Next, per-item citations. | Medium: state synchronization and stale selection. | No `generate_quiz()` change. |
| `app.py` Flashcards viewer handlers | Store set/index/reveal, one-card view and navigation. | Medium: state resets and empty results. | No `generate_flashcards()` change. |
| `app.py` Advanced/Debug and key field | Consolidate JSON and `k` controls; move blank password override out of main view. | Low–medium: ensure key never becomes an output. | Existing runtime-key path retained. |
| `static/style.css` tokens/layout/responsiveness | Replace heavy gradient/glow and fragile selectors with restrained panel classes, system font and breakpoints. | Medium: Gradio component DOM may vary; browser checks needed. | None. |
| `static/aivn_logo.png` | Candidate deletion **after** no reference remains, if separately authorized in Phase 8. | Low; do not remove in Phase 7. | None. |

No change is required in `src/indexing.py`, `src/embeddings.py`, `src/store.py`, `src/rag.py`, `src/learning.py`, `src/llm.py`, `src/schemas.py`, `src/export.py` or `src/prompts/*` for this target design.

## Phase 8 Implementation Backlog

Each item is a proposed Phase 8 task. “Backend impact: none” means the existing core call contract stays intact, even when the UI wrapper changes.

| ID | Priority | File(s) | Change | Acceptance criterion | Implementation risk | Backend impact |
|---|---|---|---|---|---|---|
| V2-01 | P0 | `app.py` | Auto-load indexed documents with `demo.load`; keep explicit selection and correct page state. | Two indexed PDFs appear on first load without Refresh or indexing. | Medium: event outputs/session state. | None; read-only listing. |
| V2-02 | P0 | `app.py`, `static/style.css` | Establish compact neutral header and Sources/Chat/Studio columns; remove rendered AIVN/course/footer/warning clutter. | Three-panel hierarchy and neutral title visible at 1366×768; no AIVN text/logo in normal UI. | Medium: layout/event relocation. | None. |
| V2-03 | P0 | `app.py` | Separate compact screen renderers from full `src.export` Markdown, with safe escaped citation details. | Q&A, Summary, Quiz and Flashcards show compact markers/filename/page; full chunks default closed; exports still contain complete output. | Medium: marker mapping/HTML escaping. | None. |
| V2-04 | P0 | `app.py` | Add source selection and empty-input guards plus concise status/error wrappers. | Empty/no-source actions show Vietnamese guidance, preserve prior results and make no Gemini call; normal UI has no traceback. | Medium: callback output consistency. | None. |
| V2-05 | P1 | `app.py` | Convert Quiz to one-question viewer with Radio, Check, reveal and navigation. | Requested valid questions can be visited; answer hidden before Check; citations match current item; export still works. | Medium: state and boundary handling. | None. |
| V2-06 | P1 | `app.py` | Convert Flashcards to single-card front/reveal/back viewer. | Only one front appears initially; answer/hint show on click; Previous/Next reset reveal; export still works. | Medium: state handling. | None. |
| V2-07 | P1 | `app.py` | Present Summary prose/key points with collapsed source list. | No full source text dominates normal summary view; all citation details remain accessible. | Low–medium: long citation list. | None. |
| V2-08 | P1 | `app.py` | Make Sources upload/list/count/status concise, preserve valid selections after refresh/upload. | Upload still indexes; selector refreshes; selected state is clear and page filter valid. | Medium: existing callback output changes. | Same ingestion call. |
| V2-09 | P1 | `app.py` | Consolidate Advanced/Debug and move runtime key override there. | JSON and `k` controls collapsed by default; `.env` key never appears in UI; override still works when entered. | Low–medium: component movement. | Same key setter. |
| V2-10 | P1 | `app.py`, `static/style.css` | Normalize primary labels to Vietnamese and remove external font import/heavy effects. | Normal panels avoid Front/Back/Hint/Sources/Scope/Textbox/Code labels and use system fonts. | Low: labels/CSS regression. | None. |
| V2-11 | P1 | `static/style.css`, `app.py` | Add desktop sizing and stacked fallback using stable `elem_classes`. | No horizontal scrolling or hidden actions at 1366×768, 1440×900, 1920×1080; narrower view stacks safely. | Medium: Gradio min widths. | None. |
| V2-12 | P2 | `app.py`, `static/aivn_logo.png` | Remove obsolete asset references and optionally delete unused logo after verification. | No missing-asset request; no AIVN asset remains referenced or served by app. | Low: reference cleanup. | None. |

## Acceptance Criteria

Phase 8 implementation and Phase 9 verification should establish all of the following:

1. No AIVN logo, AIVN text or course/provider promotional branding appears in the normal interface.
2. No warning-style introductory banner or routine development warning appears in normal UI; terminal warnings may remain.
3. Sources, Chat and Studio form a clear desktop hierarchy in Gradio.
4. Previously indexed documents appear on first page load without manual Refresh or re-indexing.
5. Upload/index still works, and selected filename(s) and count remain clear.
6. Q&A still uses existing selected-document/page filters and returns a grounded answer with markers.
7. Summary still generates and displays prose plus key points.
8. Quiz still generates valid questions and allows one-question navigation.
9. Quiz answers/explanations are hidden until the user checks or reveals them.
10. Flashcards show one front at a time, with controlled answer reveal and navigation.
11. Normal learning views show compact citation labels, not full chunk dumps.
12. Full source text, chunk IDs and raw metadata remain accessible on deliberate expansion or in Debug.
13. JSON debug is collapsed and clearly secondary; a no-op input does not erase prior valid debug output.
14. Primary user-facing labels are Vietnamese; technical debug schema may remain English.
15. Existing full Markdown exports are created and retrievable for Summary, Quiz and Flashcards; browser save should be checked again because Phase 6 did not confirm it.
16. Core RAG and learning functions, schemas and prompts remain unchanged.
17. Existing Qdrant collection and indexed PDFs suffer no data loss or unnecessary re-indexing.
18. Neither `.env` key nor runtime-entered Gemini key appears in generated content, UI state displays, export, or logs produced by the app.
19. The app works without horizontal page scrolling or hidden controls at 1366×768 and larger target resolutions.
20. Phase 4/5 backend behaviors remain valid; run focused UI regression flows after changes rather than assuming the visual redesign preserves them.

## Out of Scope

FastAPI, React, Streamlit, frontend migration, accounts/login, cloud deployment/database, Google/NotebookLM branding or assets, exact visual cloning, Audio Overview, web source discovery, video/slide generation, rerankers, hybrid retrieval, Ragas, new embedding/LLM providers, and any backend architecture rewrite. The plan does not authorize implementation or deletion in Phase 7.

## Recommended Implementation Order

1. Establish neutral shell and three-panel layout, then register document auto-load (V2-02, V2-01). Verify existing selection/upload before moving on.
2. Add compact citation/screen renderers and concise input/error feedback while retaining full exports (V2-03, V2-04, V2-07, V2-08).
3. Add Quiz and Flashcards session-state viewers (V2-05, V2-06), checking navigation boundaries and reveal resets.
4. Consolidate Advanced/Debug, normalize language and refine CSS/responsive behavior (V2-09 through V2-11).
5. Only after no references remain, decide whether to remove the old logo asset (V2-12). Then run Phase 9 browser workflows and the relevant Phase 4/5 regressions.

## Result

**PLAN READY.** The desired interface can be implemented in Gradio, primarily in `app.py` and `static/style.css`, with **zero required backend/core changes**. Phase 7 created this plan only. At planning time, `git status --short` showed a pre-existing modified `.gitignore` and untracked `reports/` and `scripts/`; no commit or push was made.
