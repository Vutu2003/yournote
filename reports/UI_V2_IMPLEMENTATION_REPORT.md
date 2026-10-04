# Phase 8 — Research Notebook UI V2 Implementation Report

Date: 2026-09-30. Final status: **PASS**. Scope: completion of the Phase 8 runtime checks; no Phase 9 work, commit, or push.

## Scope and implementation

`app.py` provides the neutral Gradio workspace with Nguồn tài liệu, Trò chuyện, and Studio; compact citations; guarded Q&A; Summary; interactive Quiz and Flashcards; full Markdown exports; and a collapsed Advanced/Debug panel. `static/style.css` provides the responsive layout. The core modules, prompts, Qdrant configuration, model configuration, and dependencies were not changed in Phase 8.

A browser defect was found during this verification: switching from Summary to Quiz or Flashcards froze both headless Chrome and Firefox. Isolated local probes showed the component shell switched tabs normally, while registering `demo.load` reproduced the freeze even with a text-only callback and with `queue=False`. The UI-only fix in `app.py` reads the current indexed-document list once at application startup and initializes the source choices/count/state from that snapshot. Refresh and upload still update the list during a session. After the fix, Quiz and Flashcards tabs opened normally. A fresh browser session showed both existing PDFs without manual Refresh or automatic indexing.

## Previously verified V2 baseline

- `app.py` compiled/imported; the original Q&A path returned a grounded answer with `[S2]`, compact closed source details, and Debug JSON. No-source and empty-question guards preserved previous results and avoided generation.
- The three panels had no horizontal page scroll at 1366×768, 1440×900, 1920×1080, or the stacked 820×900 fallback.
- The old AIVN/course/provider branding was absent from rendered UI. The old logo file remains on disk but has no `app.py` or CSS reference.

## Runtime Verification Completion

### Summary Final UI — PASS

On the final compact renderer, the browser showed Summary prose, seven key points, and a collapsed “Nguồn đã sử dụng (35)” section. Its 35 entries were short marker/filename/page labels; no full chunk text was dumped into the normal Summary HTML. Complete source details remained in the canonical Markdown export and generated-result JSON path. The Markdown component appeared, and no UI error or traceback appeared. This browser check was performed before the later document-initialization fix, which changed only startup source loading.

### Quiz V2 — PASS

| Check | Result |
|---|---|
| Generation | One request produced 3 questions from indexed PDF 4; four options appeared for question 1. |
| Answer hidden | Correct answer and explanation were absent before Check. |
| Check/reveal | Choosing option A and pressing “Kiểm tra đáp án” displayed correct/incorrect feedback, answer, and explanation. |
| Previous/Next | 1 → 2 → 3 → 2 worked; selection, answer, and sources reset on navigation; Previous was disabled on question 1 and Next on question 3. |
| Compact citations | After Check, only current-item source labels appeared inside a closed group: question 1 `[S6]`, `[S7]`, `[S18]`, `[S22]`; question 2 `[S19]`, `[S21]`. Full corpus chunks did not appear in the normal view. |
| Additional Gemini calls during checking/navigation | The registered Check/Previous/Next callbacks do not invoke the LLM; no separate provider-side call counter was instrumented. |

### Flashcards V2 — PASS

| Check | Result |
|---|---|
| Generation | One request produced 3 cards from indexed PDF 4; one front was active initially. |
| Back hidden | Back, hint, and sources were absent before Reveal. |
| Reveal | “Hiển thị đáp án” displayed the back, hint, and current-card citations; the button then disabled. |
| Previous/Next | 1 → 2 → 3 → 2 worked; the back and sources hid again on each move; Previous was disabled on card 1 and Next on card 3. |
| Compact citations | Closed current-card groups showed `[S6]`, `[S7]`, `[S18]`, `[S22]` for card 1 and `[S8]`, `[S9]` for card 2. |
| Additional Gemini calls during reveal/navigation | The registered Reveal/Previous/Next callbacks do not invoke the LLM; no separate provider-side call counter was instrumented. |

### Export Verification — PASS for generation and HTTP serving

| Export | File generation | Corresponding non-empty content | Gradio HTTP serving | Browser save |
|---|---:|---:|---:|---|
| Summary | PASS, 59,091 bytes | PASS | PASS, HTTP 200 and byte-for-byte match | NOT VERIFIED |
| Quiz | PASS, 70,822 bytes | PASS | PASS, HTTP 200 and byte-for-byte match | NOT VERIFIED |
| Flashcards | PASS, 69,413 bytes | PASS | PASS, HTTP 200 and byte-for-byte match | NOT VERIFIED |

The visible Flashcards download link was clicked in headless Chrome, but no saved file appeared in its configured download directory. Automated browser save therefore remains unverified; the generated files and Gradio file URLs were verified directly. The full Markdown format intentionally includes source text.

### Final Auto-load Check — PASS

A fresh V2 browser session showed the two indexed filenames and “2 tài liệu đã index · 100 đoạn” with zero sources preselected. No Refresh or indexing action was needed. No old-brand text or UI alert appeared. The startup snapshot reflects documents present when the app starts; a separate browser session after another session indexes a new PDF may need Refresh until the app restarts.

### Final Qdrant Integrity — PASS

The collection contained 100 points before and after verification: 65 for `2 Heart rate variability in normal and pathological sleep.pdf` and 35 for `4 Complexity analyses show two distinct types of nonlinear dynamics in short heart period variability recordings.pdf`. No upload, reindex, collection recreation, or storage cleanup was performed.

### Backend Diff Audit — PASS

`git diff --check` passed. `git diff -- src/ requirements.txt` was empty. Phase 8 source edits are limited to `app.py` and `static/style.css`. `git status --short` also showed a pre-existing modified `.gitignore` and untracked `reports/` and `scripts/`. No old-brand or `aivn_logo` reference remains in `app.py` or CSS; `static/aivn_logo.png` is an unused file and was not deleted.

### Credential Safety — PASS

`.env` is ignored by `.gitignore`. The configured Gemini key was not printed during verification. The browser's optional runtime key field was password-type and blank. An exact-key check found no key in browser HTML, the three Markdown exports, or `storage/run/app.log`. Debug output is built from generated result models rather than the key field; the previously tested Q&A Debug JSON showed no key. The Quiz/Flashcards Debug selector itself was not separately exported for an exact-key scan.

### Remaining Issues

- Minor display issue: a generated hint already prefixed with “Gợi ý:” is rendered as “Gợi ý: Gợi ý: …”. This does not affect card reveal or navigation.
- Headless Chrome browser-save confirmation remains unverified; file generation and HTTP serving passed.
- The Gradio source list is snapshotted at app startup; Refresh remains available for changes made by another session while the app stays running.
- Gradio and headless Chrome were stopped, and ports 7860/9222 were released. The Firefox diagnostic browser session was closed, but its `geckodriver` listener remained on local port 4444: SIGTERM was denied despite matching user ownership, and passwordless `sudo` was unavailable. This did not affect the V2 app or its verification.

**Final Phase 8 result: PASS.** Next authorized phase: Phase 9 final regression/acceptance testing. Phase 9 was not started. No commit or push was made.
