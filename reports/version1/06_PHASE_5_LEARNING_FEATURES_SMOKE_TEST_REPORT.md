# Phase 5 — Learning Features Smoke Test Report

Test date: 2026-09-30. Project root: /home/vutu/Desktop/rag_notebooklm/project.

## Test Scope

This phase ran exactly one operation each through the existing public Summary, Quiz, and Flashcards functions. All three used the same already indexed PDF and a filename metadata filter. The Gradio UI, export workflow, performance, architecture changes, PDF ingestion, and indexing were not tested or run.

## Environment

| Item | Observed value |
|---|---|
| Python | 3.12.10 |
| Executable | /home/vutu/Desktop/rag_notebooklm/project/.venv/bin/python |
| Gemini model | gemini-flash-lite-latest |
| Embedding model | sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 |
| Qdrant collection | rag_chunks |
| Local Qdrant path | /home/vutu/Desktop/rag_notebooklm/project/storage/qdrant |
| .env / key | .env exists; project configuration detected GEMINI_API_KEY without displaying its value |

No package, model, source setting, or API credential was changed. No Gradio process was started.

## Selected Document

- Filename: 4 Complexity analyses show two distinct types of nonlinear dynamics in short heart period variability recordings.pdf
- Path: /home/vutu/Desktop/rag_notebooklm/project/data/4 Complexity analyses show two distinct types of nonlinear dynamics in short heart period variability recordings.pdf
- Document ID in indexed metadata: 15415f078afe3933
- Indexed and filtered context chunks: 35
- Qdrant filenames before testing: only this selected PDF
- Qdrant point count before testing: 35

The PDF was already indexed from Phase 4. No PDF was reindexed or copied in this phase.

## Learning Implementation

### Summary

- Public function: src.learning.summarize.
- Application call shape: app.py passes a filename filter through the shared feature callback. This test used filters={filename: selected PDF}, with no query.
- Retrieval: when query is absent and filters are present, _resolve_target calls fetch_all_chunks; this returns all 35 matching chunks. The core query-mode fallback is settings.summarize_retrieval_k=12, but it was not used for this document-wide run.
- Strategy: settings.summarize_batch_size=10. Ten or fewer chunks use summary_single.jinja2 and one LLM call. Thirty-five chunks use four summary_map.jinja2 batches followed by one summary_reduce.jinja2 call.
- Output: src.schemas.Summary with scope, target, summary text, key points, and citations for the 35 original chunks.

### Quiz

- Public function: src.learning.generate_quiz.
- Retrieval: the same filename filter and no query caused fetch_all_chunks to supply all 35 chunks. Query-mode fallback settings.generation_retrieval_k=16 was not used. The test passed k=10 as the current Quiz UI does, but k does not limit document-wide scroll mode.
- Prompt: quiz.jinja2. Core default count is 8; this smoke test explicitly requested 3.
- Output: src.schemas.QuizSet containing QuizItem objects and citations. Each QuizItem requires four options and a correct_index within their bounds. The validator parses JSON (also accepts a simple code fence), drops invalid or duplicate questions, removes unknown source markers, and raises if no valid item remains. It does not enforce the requested item count.

### Flashcards

- Public function: src.learning.generate_flashcards.
- Retrieval: the same filename filter and no query supplied all 35 chunks. The test passed k=16 as the current Flashcards UI does, but k is unused in document-wide scroll mode.
- Prompt: flashcards.jinja2. Core default count is 15; this smoke test explicitly requested 3.
- Output: src.schemas.FlashcardSet containing Flashcard objects and citations. JSON parsing and item validation follow the same helper as Quiz, deduplicating on card front and filtering unknown markers. The schema does not enforce a requested card count or nonempty source markers.

Each function uses src.llm.invoke_llm through the current Gemini integration. An in-memory counting wrapper recorded calls to that existing function without editing source or creating a separate Gemini request.

## Summary Smoke Test

- Function: summarize(filters={filename: selected PDF}).
- Strategy: map-reduce, 4 map batches of at most 10 chunks, then 1 reduce.
- Context chunks: 35.
- Prompts involved: summary_map.jinja2 and summary_reduce.jinja2.
- Gemini calls recorded: 5.
- Returned Summary scope: filter.
- Output: nonempty Vietnamese summary (1,620 characters), 9 key points, 35 citations; Pydantic model validation passed.
- Short output description: the summary covers short heart-period series of 256 values, fetal gestation groups and an adult tilt setting, the NV% and UPI approaches, surrogate data, and two nonlinear dynamics operating at different time scales.
- Lightweight grounding: exact source text searches found 256 values, PoG1/PoG3, tilt, NV%, UPI, surrogate, and the two-types claim in the selected document's indexed chunks. This supports the summary's main themes; it is not a full check of every sentence.
- Result: PASS.

## Quiz Smoke Test

- Function: generate_quiz(filters={filename: selected PDF}, count=3, k=10).
- Context chunks: 35; k=10 was ignored by the no-query document filter path.
- Prompt: quiz.jinja2.
- Requested count: 3; returned count: 3. This count matched in this run, although source code does not guarantee it.
- Gemini calls recorded: 1.
- QuizSet and QuizItem Pydantic validation: PASS.
- Each item had nonempty question/explanation, four nonempty options, and a valid correct index.
- Sample question: “Phương pháp phân tích tính bất khả đảo theo thời gian ... tập trung vào thang thời gian nào ...?”
- Sample correct answer: very short time scales with a two-dimensional embedding space; markers S6 and S7.
- Grounding: targeted inspection of S7 found the two-dimensional embedding and very short time-scale statements. Other generated items concerned UPI and higher-dimensional embedding (S22/S23) and the linear Gaussian surrogate null hypothesis (S9/S10), also found in their cited chunks.
- Result: PASS.

## Flashcards Smoke Test

- Function: generate_flashcards(filters={filename: selected PDF}, count=3, k=16).
- Context chunks: 35; k=16 was ignored by the no-query document filter path.
- Prompt: flashcards.jinja2.
- Requested count: 3; returned count: 3. The source does not guarantee an exact count.
- Gemini calls recorded: 1.
- FlashcardSet and Flashcard Pydantic validation: PASS.
- All three cards had nonempty fronts and backs.
- Sample front: asks which time scale and embedding dimension the time-irreversibility analysis uses.
- Sample back: very short time scales and L=2 beats for NV%; markers S6, S7, and S18.
- Grounding: S7 and S18 contain those details. The other cards covered local prediction/UPI with L_min > 2 and the surrogate null hypothesis; targeted source checks found those claims in S22/S23 and S9/S10.
- Minor wording issue: the second generated back repeats the Vietnamese words “chỉ số” twice. The content and schema remain usable; no output was rewritten.
- Result: PASS.

## Zero-Context / Failure Behavior

A read-only filtered fetch for a nonexistent filename returned zero chunks. Source inspection shows each of summarize, generate_quiz, and generate_flashcards raises RuntimeError with a feature-specific “No chunks available” message before invoke_llm; it does not return an empty Summary/QuizSet/FlashcardSet. No additional Gemini call was made to test this branch. The UI was not launched, so UI presentation of these exceptions was not tested.

For malformed structured output, _parse_json accepts valid JSON or a simple fenced JSON response and raises RuntimeError on invalid JSON or a non-object/array root. Summary also checks that summary is a string and key_points is a list of strings. Quiz and Flashcards require an items/cards list, drop malformed or duplicate individual items, filter source markers to the provided context, and raise when no valid item remains. The source contains no LLM retry or JSON repair loop. No malformed output occurred in the three successful runtime operations.

## Gemini Call Count

| Feature | Calls to the existing invoke_llm function |
|---|---:|
| Summary | 5 |
| Quiz | 1 |
| Flashcards | 1 |
| Total | 7 |

These are application-level function invocations recorded during this phase. No manual retry or repeat operation was performed.

## Qdrant Integrity

- Point count before: 35.
- Point count after: 35.
- Unchanged: YES.
- Selected PDF SHA-256 before and after: identical.
- No ingestion, point deletion, collection recreation, or expected vector write occurred. The learning functions used existing indexed data and did not require Gradio.

## Result

PASS

Summary, Quiz, and Flashcards each completed once, produced schema-valid nonempty outputs materially related to the selected PDF, and left the indexed point count and PDF bytes unchanged.

## Errors / Warnings

- The Google SDK emitted a nonfatal advisory about direct automatic function calling in Models.generate_content; all seven application-level calls completed.
- The second flashcard back contains a small repeated phrase, “chỉ số chỉ số”.
- No feature error or malformed JSON occurred.

## Known Limitations Observed

- With a filename filter and no query, all matching chunks are passed to Quiz and Flashcards, and Summary uses map-reduce once the batch threshold is exceeded. The k argument does not limit that document-wide path. For this 35-chunk document, Summary made five LLM calls.
- Grounding is requested by prompts and checked here only through selected source excerpts; the project does not independently verify every generated claim.
- The structured-output path depends on Gemini returning parseable JSON. Validation can drop malformed items and does not enforce the requested item/card count or require a surviving source marker on every item.

## Source Changes

NONE. No application module, prompt, app.py, requirements.txt, static asset, indexed PDF, or .env file was edited in this phase. The only new project file is this report.

## Git Safety

- git diff for src/, app.py, requirements.txt, and static/ was empty after testing.
- .env remained ignored and its key value was not printed or included in this report.
- No commit, push, pull, or other mutating Git command was run.
- The pre-existing modified .gitignore and earlier untracked reports were not changed by this phase.
- Qdrant point count remained 35 and the selected PDF checksum remained identical.

## Recommended Next Step

Run a separately authorized PHASE 6 — GRADIO UI + USER WORKFLOW SMOKE TEST, covering launch, document selection/upload, Q&A, Summary, Quiz, Flashcards, citations, and export/debug controls as appropriate. Phase 6 was not run here.
