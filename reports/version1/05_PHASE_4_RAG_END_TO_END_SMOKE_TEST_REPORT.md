# Phase 4 — RAG End-to-End Smoke Test Report

Test date: 2026-09-30. Project root: /home/vutu/Desktop/rag_notebooklm/project.

## Test Scope

This phase tested the existing core path: selected PDF / indexed chunks → similarity retrieval → source and citation construction → answer prompt rendering → one Gemini generation through src.rag.answer → RagAnswer. Summary, Quiz, Flashcards, Gradio UI, export, benchmarking, reranking, hybrid search, and evaluation frameworks were not tested.

## Environment

| Item | Observed value |
|---|---|
| Python | 3.12.10 |
| Executable | /home/vutu/Desktop/rag_notebooklm/project/.venv/bin/python |
| .env / Gemini key | .env present; GEMINI_API_KEY detected through project configuration, value not displayed |
| Embedding model | sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 |
| Gemini model | gemini-flash-lite-latest |
| Qdrant storage | /home/vutu/Desktop/rag_notebooklm/project/storage/qdrant |
| Collection | rag_chunks |
| Core retrieval default top_k | 5; the separate Gradio Q&A slider defaults to 6 |

No dependency or configuration value was changed.

## Selected PDF

- Filename: 4 Complexity analyses show two distinct types of nonlinear dynamics in short heart period variability recordings.pdf
- Path: /home/vutu/Desktop/rag_notebooklm/project/data/4 Complexity analyses show two distinct types of nonlinear dynamics in short heart period variability recordings.pdf
- Size: 588,271 bytes; 7 pages.
- Selection: smallest of five PDFs in data/, with extractable text and a direct factual claim suitable for one deterministic question.
- Already indexed before this phase: NO. The configured collection did not yet exist and had zero points.
- Indexed through: src.indexing.save_and_ingest_pdf using only this selected file. Its content hash was the same before and after that call.
- Document ID observed in stored metadata: 15415f078afe3933.
- Chunks indexed and associated with the selected PDF: 35.
- Total collection points after indexing and after all Phase 4 checks: 35. No other PDF was indexed.

## RAG Implementation

- Public Q&A entry: src.rag.answer(question, k=None, filters={filename: selected PDF}).
- Retrieval: src.rag.retrieve calls QdrantVectorStore.similarity_search_with_score with k or settings.top_k and a Qdrant metadata filter. It returns RetrievedChunk objects containing text, float score, and ChunkMetadata.
- UI relationship: app.py calls answer directly; a single selected document is normalized to a filename filter. This smoke test used the core default k=5 rather than the UI slider default k=6.
- Prompt: src.rag.render_prompt loads src/prompts/answer.jinja2 through Jinja with StrictUndefined. Retrieved chunks are rendered as numbered source context.
- Generation: src.llm.invoke_llm makes the configured Gemini generate_content call and returns stripped plain text.
- Output: src.rag.answer returns RagAnswer with the question, stripped answer, all retrieved chunks, and one Citation per retrieved chunk. The LLM answer is not parsed as JSON or checked against source claims.
- Zero-context source branch: answer returns the fixed Vietnamese insufficient-context message with empty citations/chunks before invoking Gemini.

## Test Question

Question: “How many distinct types of nonlinear dynamics did the complexity analyses show in short heart period variability recordings?”

Expected factual answer from page 1 of the selected PDF: two distinct types. The same passage says they are characterized by different ranges of time scales. The question is narrow, answerable from that passage, and does not require outside knowledge. It was fixed before retrieval and not revised after seeing results.

## Retrieval Result

A standalone call to the actual src.rag.retrieve function used the selected filename filter and the core default top_k=5. Five chunks were returned. All had the selected filename and document ID 15415f078afe3933. Scores below are the numeric values exposed by similarity_search_with_score; they are not calibrated probabilities.

| Marker / rank | Score | Page | Chunk ID | Short excerpt / relevance |
|---|---:|---:|---|---|
| S1 / 1 | 0.728105 | 5 | 15415f078afe3933:5:20 | “percentage of healthy humans exhibiting nonlinear dynamics” — related, not the direct count claim. |
| S2 / 2 | 0.724162 | 1 | 15415f078afe3933:1:2 | “two distinct types of nonlinear HP dynamics characterized by diverse ranges of time scales” — direct support. |
| S3 / 3 | 0.715247 | 6 | 15415f078afe3933:6:27 | Bibliography near “Predicting chaotic time series” — weak relevance. |
| S4 / 4 | 0.705186 | 2 | 15415f078afe3933:2:4 | Discussion of nonlinear methods for short HP variability — related background. |
| S5 / 5 | 0.659280 | 3 | 15415f078afe3933:3:10 | Discussion of original series and nonlinearities — related background. |

Retrieval: PASS. At least one returned chunk, S2, explicitly answers the fixed question. The other chunks show that top-k retrieval can include tangential material, especially without a similarity threshold or reranker.

## Citation / Source Construction

src.rag.format_citations generated S1, S2, S3, S4, and S5 in retrieved order. Each Citation's filename, page, and chunk ID matched its corresponding RetrievedChunk. The filename for every marker is the selected PDF listed above.

| Marker | Filename | Page | Chunk ID |
|---|---|---:|---|
| S1 | Selected PDF | 5 | 15415f078afe3933:5:20 |
| S2 | Selected PDF | 1 | 15415f078afe3933:1:2 |
| S3 | Selected PDF | 6 | 15415f078afe3933:6:27 |
| S4 | Selected PDF | 2 | 15415f078afe3933:2:4 |
| S5 | Selected PDF | 3 | 15415f078afe3933:3:10 |

Citation/source construction: PASS. Numbering was deterministic for this call. The final answer referenced S2, which maps to the direct supporting passage. The RagAnswer object still returns all five citation objects, including sources not cited in the answer text.

## Prompt Rendering

- Template: src/prompts/answer.jinja2, rendered through src.rag.render_prompt.
- Test question included: YES.
- Retrieved context included: YES.
- Source markers included: YES; context uses [source=S1] through [source=S5].
- Context-only grounding instruction present: YES.
- Inline [S#] citation instruction present: YES.
- Prompt rendering: PASS.

The full prompt and full chunks are omitted from this report.

## End-to-End RAG Result

- Function used: src.rag.answer with k=None and a filename filter for the selected PDF.
- Gemini generation calls initiated by this test: exactly 1, through the normal answer path; no manual retry or separate Gemini request was made.
- Model: gemini-flash-lite-latest.
- Final answer: “Các chỉ số độ phức tạp đã chỉ ra sự hiện diện của hai loại động lực học phi tuyến tính (HP dynamics) riêng biệt, được đặc trưng bởi các dải thời gian khác nhau [S2].”
- Returned chunks: 5.
- Returned Citation objects: 5 (S1–S5).
- Citation marker referenced in the answer: [S2]; it is present among the returned sources.
- RagAnswer.model_validate(result.model_dump()) completed: PASS.

## Grounding Validation

| Check | Result | Evidence |
|---|---|---|
| Relevant source returned | YES | S2 contains the direct “two distinct types” claim. |
| Answer agrees with the PDF | YES | “Hai loại” matches the PDF; different time-scale ranges are also in S2. |
| Citation marker present | YES | Final answer contains [S2]. |
| Marker maps to a returned source | YES | S2 is page 1, chunk 15415f078afe3933:1:2 of the selected PDF. |
| Unsupported claim observed | NO | The short answer's substantive claims are in S2. |
| Factual mismatch observed | NO | None in the returned answer. |

This is a manual check of one answer. The source code does not enforce statement-level citation correctness; it relies mainly on prompt instructions and returns Citation objects for all retrieved chunks.

## Insufficient Context Behavior

A retrieval-only check using an impossible filename filter returned zero chunks and made no Gemini call. Source inspection of src.rag.answer confirms that when retrieve returns an empty list, it returns a RagAnswer with “Tôi không có đủ thông tin trong ngữ cảnh được cung cấp để trả lời.” and empty citations/chunks before invoke_llm. The answer function itself was not called again for this branch, preserving the single Gemini generation test.

## Result

PASS

The selected PDF was indexed; retrieval returned directly relevant context; citation construction and prompt rendering passed; one normal Gemini RAG call completed; the RagAnswer schema validated; and the answer was materially grounded in the PDF.

## Errors / Warnings

- The selected PDF produced several pypdf warnings about duplicate /MediaBox definitions, but text extraction and indexing succeeded.
- Local Qdrant warned that payload indexes have no effect in embedded mode. Indexing and filtered retrieval succeeded.
- Hugging Face Hub warned that model access was unauthenticated; model loading succeeded.
- The Google SDK emitted a nonfatal advisory about direct automatic function calling in Models.generate_content. Generation succeeded.
- A nonfatal Qdrant client destructor warning appeared at interpreter shutdown after the standalone retrieval precheck. Subsequent checks closed the client explicitly.

No stage failed.

## Source Changes

NONE. No source file, prompt, app.py, requirements.txt, or dependency was modified. The expected runtime change was creation of the non-destructive local Qdrant collection and 35 points for the selected PDF. The file in data/ retained identical bytes after the upload/index call. This report is the only new project file from this phase.

## Git Safety

- git diff for src/, app.py, requirements.txt, and static/ was empty after testing.
- No commit, push, pull, or other mutating Git command was run.
- .env remained ignored; the Gemini key was detected by presence only and was not printed.
- Qdrant storage was not wiped or recreated destructively; only the selected PDF was indexed.
- The modified .gitignore and earlier untracked reports were present before Phase 4 and were not changed by it.

## Known Limitations Observed

- Retrieval uses dense similarity search without a score threshold or reranker. One of the top five hits was a bibliography chunk despite the direct supporting hit at rank 2.
- Citation compliance is requested in the prompt, not verified statement by statement in code. All retrieved chunks are returned as Citation objects even when the answer references only S2.
- The current indexing path uses deterministic IDs and upserts, but does not remove obsolete points if a previously indexed PDF changes or becomes shorter. This test indexed a previously unindexed PDF, so it did not exercise that risk.

## Recommended Next Step

In a separately authorized PHASE 5 — Learning Features Smoke Test, test Summary, Quiz, and Flashcards individually. Phase 5 was not run here.
