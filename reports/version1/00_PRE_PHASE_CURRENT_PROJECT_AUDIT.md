# Current Project Technical Audit — Before Phase 1

Audit date: 2026-09-30. Scope: the current files under `project/` in this workspace. Method: source inspection only; no imports, application startup, model inference, network requests, ingestion, or evaluation were run. `docs/[Description]-Building-Simple-NotebookLM.pdf` is outside the application tree and was not used as implementation evidence.

## 1. Executive Summary

The project is a PDF based study RAG application with question answering, summaries, quizzes, and flashcards. `app.py` is a **Gradio** UI; there is no Streamlit implementation in the current source. UI callbacks call local Python core functions directly. PDF pages are chunked, embedded with a local Sentence Transformers model, and stored in an on disk Qdrant collection. Retrieval supplies Jinja prompts to the sole configured LLM backend, Google's Gemini API (`google-genai`). See `app.py:9-18`, `src/indexing.py:49-113`, `src/store.py:32-68`, `src/rag.py:20-120`, and `src/llm.py:18-41`.

Static readiness: the code describes a complete path, but end to end operation is **NOT VERIFIED**. A Gemini API key is needed for any feature that invokes the LLM, supplied in the UI or through `GEMINI_API_KEY`. PDF indexing and retrieval need the embedding model available and writable local paths. No `.env`, `data/`, or `storage/` exists in the inspected project tree; `.env` is optional because defaults and the UI key field exist. No REST server, vLLM, local Hugging Face LLM, or reranker is implemented.

## 2. Project Structure

```text
rag_notebooklm/
├── docs/
│   └── [Description]-Building-Simple-NotebookLM.pdf
└── project/                         # application/repository root
    ├── .git/                        # repository metadata, not application source
    ├── .gitattributes
    ├── .gitignore
    ├── README.md                     # Hugging Face Spaces YAML metadata
    ├── requirements.txt
    ├── app.py                        # Gradio UI and callbacks
    ├── reports/                      # empty before this audit
    │   └── 00_PRE_PHASE_CURRENT_PROJECT_AUDIT.md
    ├── static/
    │   ├── aivn_logo.png
    │   └── style.css
    └── src/
        ├── __init__.py
        ├── config.py                 # Pydantic settings
        ├── embeddings.py             # Sentence Transformers adapter
        ├── indexing.py               # PDF load, split, ingest, upload
        ├── store.py                  # local Qdrant client and collection
        ├── filters.py                # metadata filter normalization
        ├── rag.py                    # retrieve, prompts, answer, citations
        ├── llm.py                    # Gemini invocation
        ├── learning.py               # summary, quiz, flashcards
        ├── schemas.py                # Pydantic data contracts
        ├── export.py                 # Markdown/text/JSON rendering
        └── prompts/
            ├── answer.jinja2
            ├── summary_single.jinja2
            ├── summary_map.jinja2
            ├── summary_reduce.jinja2
            ├── quiz.jinja2
            └── flashcards.jinja2
```

`src/__init__.py` only marks the package. `.gitignore` excludes `__pycache__/`, `storage/`, `data/`, and `exports/`; it does not list `.env` (`.gitignore:1-4`). `.gitattributes` defines Git LFS patterns for binary/model/archive formats; the source does not load a bundled model from these files. Paths such as `data`, `storage/qdrant`, `static/style.css`, and `exports` are relative to the process working directory, so launch from `project/` is the path arrangement implied by the code (`src/config.py:23-24`, `app.py:40`, `app.py:254`, `app.py:287`).

## 3. Overall Architecture

### Indexing pipeline

PDF discovery or Gradio upload → `PyPDFLoader` page documents → page/source metadata → `RecursiveCharacterTextSplitter` → stable chunk metadata/IDs → Sentence Transformers embeddings → local Qdrant upsert (`src/indexing.py:49-172`).

### Query / RAG pipeline

Question and optional metadata filters → Qdrant similarity search → `RetrievedChunk` objects → Jinja `answer.jinja2` → Gemini `generate_content` → `RagAnswer` with a citation entry for each retrieved chunk (`src/rag.py:20-120`). With no hits, `answer()` returns the fixed insufficient-context answer without calling Gemini.

### Learning-feature pipeline

Optional query → similarity search; otherwise document/filter/corpus → Qdrant scroll of all matching chunks. Summary uses one LLM call at up to ten chunks, otherwise per-batch map calls and one reduce call. Quiz and flashcards use one prompt and JSON parsing/validation (`src/learning.py:39-227`).

### UI pipeline

Gradio event → local callback in `app.py` → core Python function → Markdown plus JSON debug output; summary/quiz/flashcards can be written to `exports/*.md` for download (`app.py:180-273`, `app.py:442-483`). No HTTP application backend is called by this UI.

## 4. Configuration Audit

`Settings` is instantiated on importing `src.config`, cached by `get_settings()`, and reads an optional `.env` plus environment values (`src/config.py:16-60`). Except the explicit Gemini key alias, fields use the `RAG_` prefix. Defaults below are code defaults, not observed effective runtime values.

| Config | Current value/default | Purpose | Risk / Note |
|---|---|---|---|
| `data_dir` | `data`; `RAG_DATA_DIR` | PDF upload/discovery | Relative to working directory; upload creates it. |
| `storage_dir` | `storage/qdrant`; `RAG_STORAGE_DIR` | Local Qdrant files | Must be writable; client creates directory. |
| `qdrant_collection` | `rag_chunks`; `RAG_QDRANT_COLLECTION` | Collection name | Existing collection must match embedding size/index schema. |
| `chunk_size` | `1500`; `RAG_CHUNK_SIZE` | Character splitter size | `>=500`; must exceed overlap. |
| `chunk_overlap` | `200`; `RAG_CHUNK_OVERLAP` | Character overlap | `>=0`, `< chunk_size`. |
| `top_k` | `5`; `RAG_TOP_K` | Default answer retrieval | `1..64`; UI Q&A supplies `6` by default. |
| `llm_provider` | `gemini`; `RAG_LLM_PROVIDER` | Provider selection | Literal accepts only `gemini`; implementation does not dispatch on this field. |
| `llm_model` | `gemini-flash-lite-latest`; `RAG_LLM_MODEL` | Gemini model ID | Availability/permissions unverified. |
| `llm_temperature` | `0.1`; `RAG_LLM_TEMPERATURE` | Generation temperature | `0..2`. |
| `llm_max_new_tokens` | `10000`; `RAG_LLM_MAX_NEW_TOKENS` | Gemini `max_output_tokens` | `1..20000`; provider limit unverified. |
| `embedding_provider` | `local`; `RAG_EMBEDDING_PROVIDER` | Embedding provider label | Literal accepts only `local`; implementation does not dispatch on it. |
| `embedding_model` | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`; `RAG_EMBEDDING_MODEL` | Sentence Transformers model | May require initial model retrieval/cache. |
| `gemini_api_key` | `None`; **`GEMINI_API_KEY`** | Gemini authentication | Required only when invoking Gemini, unless UI supplies runtime key. |
| `summarize_batch_size` | `10`; `RAG_SUMMARIZE_BATCH_SIZE` | Summary map batch size | `>=1`; larger corpus increases calls. |
| `summarize_retrieval_k` | `12`; `RAG_SUMMARIZE_RETRIEVAL_K` | Query summary fallback `k` | `1..128`; UI passes `10`. |
| `generation_retrieval_k` | `16`; `RAG_GENERATION_RETRIEVAL_K` | Query quiz/card fallback `k` | `1..128`; UI passes `10`/`16`. |
| `quiz_default_count` | `8`; `RAG_QUIZ_DEFAULT_COUNT` | Core quiz count | `1..50`; UI passes `3`. |
| `flashcards_default_count` | `15`; `RAG_FLASHCARDS_DEFAULT_COUNT` | Core card count | `1..100`; UI passes `15`. |

There is **no** embedding-device setting, API URL, Qdrant server URL, or explicit summary length/count setting. Invalid settings can fail during `src.config` import; `chunk_overlap >= chunk_size` is rejected by the model validator (`src/config.py:47-60`). `_splitter()` uses `chunk_size or default` and `chunk_overlap or default`, so an explicit zero overlap argument is replaced by the configured default (`src/indexing.py:26-35`).

## 5. Environment Variables

The names below derive from the actual Pydantic `env_prefix="RAG_"` fields and the explicit `GEMINI_API_KEY` alias (`src/config.py:16-45`). All `RAG_` overrides are optional. The table's default column refers to the corresponding Python setting.

| Variable | Required? | Used by | Default | Notes |
|---|---|---|---|---|
| `RAG_DATA_DIR` | No | indexing | `data` | Relative path by default. |
| `RAG_STORAGE_DIR` | No | store | `storage/qdrant` | Local, writable path. |
| `RAG_QDRANT_COLLECTION` | No | store/RAG | `rag_chunks` | Collection name. |
| `RAG_CHUNK_SIZE` | No | indexing | `1500` | Minimum 500. |
| `RAG_CHUNK_OVERLAP` | No | indexing | `200` | Nonnegative, less than chunk size. |
| `RAG_TOP_K` | No | RAG | `5` | UI passes its own Q&A `k`. |
| `RAG_LLM_PROVIDER` | No | config | `gemini` | Only `gemini` validates. |
| `RAG_LLM_MODEL` | No | LLM | `gemini-flash-lite-latest` | Provider model ID. |
| `RAG_LLM_TEMPERATURE` | No | LLM | `0.1` | Range 0–2. |
| `RAG_LLM_MAX_NEW_TOKENS` | No | LLM | `10000` | Range 1–20000. |
| `RAG_EMBEDDING_PROVIDER` | No | config | `local` | Only `local` validates. |
| `RAG_EMBEDDING_MODEL` | No | embeddings | multilingual MiniLM model above | Must match existing collection dimension. |
| `GEMINI_API_KEY` | Conditional | LLM | `None` | Needed for LLM calls if runtime UI key is absent; no `RAG_` prefix for this alias. |
| `RAG_SUMMARIZE_BATCH_SIZE` | No | learning | `10` | Map batch threshold. |
| `RAG_SUMMARIZE_RETRIEVAL_K` | No | learning | `12` | Query fallback. |
| `RAG_GENERATION_RETRIEVAL_K` | No | learning | `16` | Query fallback. |
| `RAG_QUIZ_DEFAULT_COUNT` | No | learning | `8` | Core default. |
| `RAG_FLASHCARDS_DEFAULT_COUNT` | No | learning | `15` | Core default. |

The repository contains no `.env` file at inspection time. Code permits either an optional `.env` or process environment values; it does not require creating `.env`. The Gradio key field also supplies a per-callback runtime key via `ContextVar` (`app.py:180-185`, `app.py:260-273`, `src/llm.py:13-27`).

## 6. LLM Backend Audit

`src/llm.py` implements exactly one backend. It creates `google.genai.Client(api_key=...)` for each invocation and calls `client.models.generate_content()` with the configured model, temperature, and `max_output_tokens`. Empty response text raises `RuntimeError` (`src/llm.py:18-41`).

| Provider | Local/Cloud | Model | Needs API Key | GPU Need | Current readiness |
|---|---|---|---|---|---|
| `gemini` | Cloud | `gemini-flash-lite-latest` by default | Yes for generation, via UI or `GEMINI_API_KEY` | No local GPU indicated | **NEEDS CONFIG** for LLM use; availability and API result **NOT VERIFIED**. |

No `hf_local`, vLLM, alternate cloud provider, endpoint URL, or local LLM path appears in the implementation. A typical personal computer can host the Python client side in principle; successful use depends on service access and the configured key/model, which this audit did not test. The `llm_provider` setting is restricted to `gemini` and is not read inside `invoke_llm()`.

## 7. Embedding Audit

`src/embeddings.py:7-31` adapts `sentence_transformers.SentenceTransformer` to LangChain `Embeddings`. The default model ID is `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`. `_model()` loads lazily on first embedding call and caches one model per process with `lru_cache(maxsize=1)`. Document and query embeddings both call `encode(..., normalize_embeddings=True)`. There is no explicit `device`, batch-size, or disk-cache setting in project code; Sentence Transformers chooses its own device behavior. The model identifier refers to a Hugging Face model and may require a download if uncached; no download was attempted.

Dimension is **measured at collection creation**, using `len(embed_query("dimension probe"))`, rather than hard coded (`src/store.py:49-57`). This audit did not load the model, so it does not claim a measured dimension. Changing model on an existing collection can leave a vector-size mismatch because existing collections are not rebuilt automatically.

## 8. Vector Store Audit

`QdrantClient(path=str(settings.storage_dir))` uses embedded, on disk **local Qdrant**, not an HTTP server (`src/store.py:32-36`). The client is cached, with a `close_client()` helper. Default path is `storage/qdrant`, default collection `rag_chunks`, and collection creation uses COSINE distance and the measured embedding dimension. `ensure_collection()` optionally deletes/recreates a named collection when called with `recreate=True`; the UI upload path uses `recreate=False` (`src/store.py:39-76`, `src/indexing.py:164`).

Payload indexes are requested for `metadata.document_id` and `metadata.filename` as keywords and `metadata.page` as integer. Existing index schema is checked; mismatch raises `ValueError`. LangChain `QdrantVectorStore.add_documents()` writes chunks with UUIDv5 point IDs derived from `chunk_id` (`src/indexing.py:105-114`). Repeat ingestion of the same chunk IDs is intended to upsert, but there is no cleanup of obsolete point IDs for changed or shortened documents. `scroll_all()` pages through points without vectors, and `list_documents()` derives document summaries from stored metadata (`src/store.py:79-151`).

## 9. Document Ingestion Audit

`discover_pdfs()` lists PDF files only at the top level of `data/`, sorted by name; it returns an empty list if the directory is absent (`src/indexing.py:65-69`). `_load_pdf()` uses `PyPDFLoader.load()`, annotates each page with `document_id`, filename, absolute resolved source path, 1-based page number, and optional section (`src/indexing.py:40-62`). The ID is the first 16 hex characters of SHA-1 of `filename:file_size`, not a hash of PDF bytes (`src/indexing.py:40-42`).

The default `RecursiveCharacterTextSplitter` has size 1500, overlap 200, separators `\n\n`, `\n`, `. `, space, then empty string, with `keep_separator=False` (`src/indexing.py:26-37`). Each chunk receives a `chunk_id` of `document_id:page:per_document_counter`; that counter runs across chunks of the same document, including pages (`src/indexing.py:88-102`). Point IDs are UUIDv5 of chunk IDs.

The Gradio upload accepts multiple `.pdf` selections, reads bytes, sanitizes the filename to its basename, creates `data/`, writes the bytes, ensures the Qdrant collection, and indexes only the newly uploaded file (`app.py:60-95`, `app.py:305-311`, `src/indexing.py:145-172`). It checks filename extension and nonempty bytes; `PyPDFLoader` is the substantive PDF parse check. Existing PDF files with the same basename are overwritten. There is no content-hash duplicate detection, existing-point deletion, or transactional rollback for an upload that fails after writing.

## 10. Retrieval Audit

`retrieve()` uses `QdrantVectorStore.similarity_search_with_score(query, k, filter)` and maps hits into `RetrievedChunk` (`src/rag.py:20-39`). Default `k` is `settings.top_k=5`, while UI sliders pass 6 for Q&A, 10 for summary/quiz, and 16 for flashcards (`app.py:374-427`). No similarity cutoff, hybrid search, reranking, or score threshold is in source.

Filters support `filename`, `filenames`, `page`, `section`, and `document_id`, combined as Qdrant `must` conditions; multiple filenames use `MatchAny`. The filter validator removes a page filter when more than one filename is selected (`src/filters.py:9-85`). The UI exposes filename selection and a page selector when exactly one filename is selected (`app.py:98-104`, `app.py:128-134`, `app.py:351-359`). `section` and `document_id` exist in the core filter model but have no UI control.

`format_citations()` assigns `[S1]`, `[S2]`, etc. to every retrieved chunk and includes filename, page, full source text, section, and chunk ID. The code does not verify that the generated answer cites only these markers or that each citation actually supports the answer (`src/rag.py:83-120`). If zero chunks are retrieved, `answer()` returns an insufficient-context response with empty citations/chunks and skips the LLM (`src/rag.py:104-120`).

`fetch_all_chunks()` scrolls all matching payloads, omits records missing metadata/text, gives them score `0.0`, and sorts by filename, page, and chunk index (`src/rag.py:42-64`). It is used by learning features without a query, so a document/filter/corpus summary can cover all matching indexed chunks instead of only top-k hits (`src/learning.py:39-64`).

## 11. Prompt Audit

All six templates are in `src/prompts/` and rendered by a Jinja environment using `StrictUndefined` (`src/rag.py:67-80`).

| Template | Used for | Expected output | Notes |
|---|---|---|---|
| `answer.jinja2` | Q&A | Vietnamese prose with `[S#]` citations | Instructs context only, no invention, exact insufficient-context sentence. |
| `summary_single.jinja2` | Summary of up to one batch | JSON `summary`, `key_points` | Context only; asks for empty result if context empty/unrelated. |
| `summary_map.jinja2` | Partial summary of a chunk batch | Same JSON shape | Context only; 4–8 sentences target. |
| `summary_reduce.jinja2` | Merge partial summaries | Same JSON shape | Uses only partials; no original chunks in reduce prompt. |
| `quiz.jinja2` | Multiple choice questions | JSON `items` with 4 options, index, explanation, markers, difficulty, topic | Context only; may output fewer than requested if insufficient. |
| `flashcards.jinja2` | Study cards | JSON `cards` with front/back/hint/topic/markers | Context only; may output fewer than requested. |

All prompts contain grounding or anti-fabrication instructions. Answer and quiz explicitly require source markers; flashcards request one when possible. Summary templates do not require citations inside the summary JSON, although the returned `Summary` attaches citations for all input chunks. Quiz/flashcard templates demand strict JSON. Prompt instructions are safeguards by request, not an enforced factuality check (`src/learning.py:67-112`, `src/rag.py:83-120`).

## 12. Learning Features Audit

`_resolve_target()` uses query similarity retrieval when `query` is present; otherwise it scrolls all chunks matching document or filters, or the whole corpus. `document` adds a filename filter. It returns scope `query`, `document`, `filter`, or `corpus` and a target label (`src/learning.py:39-64`). No chunks causes each feature to raise `RuntimeError` before calling the LLM.

| Feature | Input and retrieval | LLM / output | Citation and validation |
|---|---|---|---|
| `summarize()` | Optional document/query/filter/`k`; query default 12; no query fetches all matching chunks | Single JSON summary at ≤10 chunks; otherwise map each batch then reduce | Validates summary string and string-list key points; attaches citations for all original chunks, without per-statement mapping (`src/learning.py:115-160`). |
| `generate_quiz()` | Same scope choices; query default 16; default 8 items | One JSON generation; `QuizSet` of `QuizItem` | Exactly four options and valid `correct_index` enforced; drops invalid/duplicate questions, filters unknown markers, requires at least one valid item; does not enforce requested count or nonempty marker list (`src/learning.py:67-100`, `src/learning.py:163-193`). |
| `generate_flashcards()` | Same scope choices; query default 16; default 15 cards | One JSON generation; `FlashcardSet` of `Flashcard` | Drops invalid/duplicate fronts, filters unknown markers, requires at least one valid card; does not enforce requested count or nonempty marker list (`src/learning.py:196-227`). |

`_parse_json()` accepts a JSON object or array and strips a simple Markdown code fence; feature validators then require the expected object/list structure. There is no JSON repair/retry or provider structured-output mode (`src/learning.py:22-36`, `src/learning.py:67-112`). A large no-query corpus may yield many map calls and a large reduce prompt, without a source-level size cap (`src/learning.py:133-152`).

## 13. Schema Audit

`src/schemas.py` defines: `ChunkMetadata` (document identity, source, page, chunk ID, section); `RetrievedChunk` (text, score, metadata); `Citation` (source marker and location/text); `RagAnswer` (question, answer, citation and chunk lists); `Summary` (scope, target, summary, key points, citations); `QuizItem` and `QuizSet`; `Flashcard` and `FlashcardSet` (`src/schemas.py:9-106`). `QuizItem` alone has a custom validator for correct answer index. The option list is constrained to exactly four by Pydantic. `Summary`, `QuizSet`, and `FlashcardSet` share the scope literal `query|document|filter|corpus`. `MetadataFilter` is separately defined in `src/filters.py:9-35`. These are data contracts; they do not verify factual support for generated text.

## 14. Streamlit / UI Audit

**No Streamlit UI is present.** `README.md:1-9` declares a Hugging Face Space with `sdk: gradio`, `sdk_version: 6.13.0`, and `app_file: app.py`; `requirements.txt:1` pins Gradio. `app.py:285-483` builds a `gr.Blocks` page titled “Building a Simple NotebookLM”, with a header/logo, information note, two main columns for upload/config and document selection, then tabs for Q&A, summary, quiz, and flashcards. There is no Streamlit sidebar. Gradio accordions hold the Gemini key, usage notes, configuration display, advanced controls, and JSON debug views.

The app accepts multiple PDF uploads, lists indexed documents, permits filename selection and single-document page filtering, displays Q&A in a chatbot, renders citations through Markdown/HTML `<details>` blocks, and exposes raw JSON. Summary/quiz/cards each have a Markdown download written to `exports/`; Q&A has no download widget (`app.py:251-257`, `app.py:361-477`, `src/export.py:16-161`). `static/style.css` contains selectors for the Gradio layout and features; `static/aivn_logo.png` is read and embedded in the header (`app.py:40-45`, `app.py:285-288`). `demo.queue(default_concurrency_limit=2).launch(...)` is the direct entry point.

**UI calls core Python functions directly**, including indexing, listing, answering, and learning generation (`app.py:11-18`, `app.py:137-273`). There is no separate FastAPI server dependency, API URL, or HTTP base URL. It can be started as a single Gradio process in principle, provided dependencies, model availability, local write access, and (for generation) a Gemini key. Actual launch behavior was not tested.

## 15. API / External-Service Audit

**No REST API layer found in the current source tree.** No FastAPI routes or app-side HTTP request client appear. The only explicit external service call is Gemini through the `google-genai` SDK in `src/llm.py:29-37`. The embedding model can require a Hugging Face download on first load; Qdrant itself is local on disk. No API base URL or endpoint is configured in project source. Gradio provides its own app serving when launched, but the UI callbacks do not call a separate backend service.

## 16. Dependencies Audit

`requirements.txt` declares:

| Group | Packages / source use |
|---|---|
| Core Python / config | `pydantic`, `pydantic-settings`; `python-dotenv` is for `.env` support via settings, not directly imported. |
| RAG / LangChain | `langchain-core`, `langchain-community`, `langchain-text-splitters`, `langchain-qdrant`. |
| Embedding | `sentence-transformers`. |
| Vector database | `qdrant-client`. |
| LLM providers | `google-genai`. |
| UI | `gradio[mcp,oauth]==6.13.0`; the code imports Gradio but does not explicitly use MCP or OAuth APIs. |
| PDF handling | `pypdf` for `PyPDFLoader` support. |
| Evaluation | None declared or implemented. |
| Utility | `jinja2`, `loguru`. |

Sentence Transformers and its transitive model/runtime stack are likely the heaviest install/model-cache cost. Local embedding can use CPU; GPU support depends on its transitive runtime rather than a project-level device setting. Gradio is pinned, while most other packages use ranges or only lower bounds (`google-genai>=1.0.0`, `sentence-transformers>=5.0.0`); compatibility across all resolved versions is **NOT VERIFIED**. No directly imported third-party package is clearly missing from `requirements.txt`; `python-dotenv`, Gradio MCP/OAuth extras, and `pypdf` are indirect or optional at source level. Python version is not specified; the annotations `str | None` require Python 3.10 or newer. No evaluation dependency or script is in the inspected source.

## 17. Hardware Requirements

| Component | Code-level hardware assessment |
|---|---|
| PDF parsing, splitting, local Qdrant, Gradio | CPU and writable disk; no GPU use indicated. |
| Sentence Transformers embedding | Local inference, GPU optional in principle; no device is forced in source. CPU feasibility depends on machine resources and model availability; untested. |
| Gemini LLM | Remote service; no local LLM GPU indicated. Requires network/service access and valid key for generation. |
| Hugging Face local LLM | Not implemented; no requirement to assess. |
| vLLM | Not implemented; no requirement to assess. |
| Reranker | Not implemented; no requirement to assess. |

The source establishes **no GPU-required component** and no GPU hard-coded setting. Memory, disk, latency, and actual CPU performance were not benchmarked.

## 18. Current Run Readiness

Statuses here express only static evidence. **READY** means the code path has no obvious mandatory missing configuration; it does not mean execution was tested.

| Component | Status | Reason |
|---|---|---|
| Config | READY | Defaults cover non-secret settings; optional `.env`; invalid overrides can fail at import. |
| PDF ingestion | NOT VERIFIED | Upload path creates `data/`, but parsing, model load, and writing were not executed; no preloaded `data/` PDFs exist in project tree. |
| Embedding | NOT VERIFIED | Model loads lazily and may need retrieval/cache; no model inference run. |
| Qdrant | NOT VERIFIED | Local path is created in code; permissions, collection creation, and installed API compatibility untested. |
| Retrieval | NOT VERIFIED | Search path exists, but needs an indexed collection; no search run. |
| LLM | NEEDS CONFIG | Runtime UI key or `GEMINI_API_KEY` required for generation; model/service access untested. |
| Gradio UI | NOT VERIFIED | Entry point and callbacks exist, but Gradio app was not started; static asset paths depend on working directory. |
| Evaluation | BLOCKED | No evaluation implementation/dependency found in source. |

## 19. Potential Issues / Risks

| Severity | Finding | Evidence / likely effect |
|---|---|---|
| High | Same filename upload overwrites `data/<name>`; document ID hashes filename plus file size, not content. | `src/indexing.py:40-42`, `src/indexing.py:158-162`. Different equal-size content can reuse IDs; changed size can leave old points. |
| High | Reindex does not remove obsolete points when a PDF changes or produces fewer chunks. | `src/indexing.py:105-114`, `src/indexing.py:164-172`. Search/list may include stale content. |
| Medium | Relative data/storage/static/export paths depend on launch directory. | `src/config.py:23-24`, `app.py:40`, `app.py:254`, `app.py:287`. Running outside `project/` may fail to read assets or use an unintended store. |
| Medium | Existing collection vector size is not checked against a changed embedding model at configuration time. | `src/store.py:49-59`, `src/store.py:109-114`. Runtime indexing/query can fail after model change. |
| Medium | No-query learning path can pass all chunks through many map calls or a large prompt without a corpus cap. | `src/learning.py:39-64`, `src/learning.py:133-152`, `src/learning.py:181-219`. Higher latency/cost or context limits are possible. |
| Medium | Model JSON validity and citation grounding rely partly on prompt compliance. | `src/learning.py:22-112`, `src/rag.py:83-120`. Invalid JSON raises; unknown quiz/card markers are stripped, but nonempty markers and support are not enforced. |
| Medium | `requirements.txt` has loose bounds for Gemini/embedding packages and several LangChain ranges. | `requirements.txt:4-18`. Resolved compatibility and Gradio launch API need actual environment verification. |
| Low | `_splitter()` cannot accept explicit `chunk_overlap=0` because it falls back with `or`. | `src/indexing.py:29-30`. Config-level zero remains possible. |
| Low | `list_documents()` groups by filename and keeps the first document ID for that name. | `src/store.py:117-151`. Distinct indexed versions of one filename appear as one document summary. |
| Low | `.env` is not ignored if a future operator creates it in the repository. | `.gitignore:1-4`; no `.env` exists now. |
| Low | A UI label says “Cấu hình chạy trên Space”, but no alternate runtime backend is implemented. | `app.py:331-340`. This is a deployment label, not a backend configuration control. |

No source evidence supports a hard-coded GPU, local LLM model path, FastAPI dependency, or Qdrant server URL. No Critical finding is established from static inspection alone.

## 20. What Must Be Configured Before First Run

For a first **generation** run via the current UI:

- [ ] Install the declared dependencies in a compatible Python 3.10+ environment and launch from `project/` so relative assets and storage paths resolve as coded.
- [ ] Ensure local storage and model cache locations are writable and the embedding model is available locally or retrievable when first used.
- [ ] Upload at least one readable PDF through the UI (or place PDFs in `data/` and invoke `ingest()` from Python); wait for indexing before relying on retrieval.
- [ ] Supply a valid Gemini key through the Gradio field or `GEMINI_API_KEY`, and ensure the configured Gemini model is accessible.

Creating `.env`, setting an API URL, starting FastAPI/Qdrant server, configuring GPU, or adding a local LLM is **not** required by the current source. Those would be separate deployment/design choices.

## 21. Recommended Minimal-Change Strategy

The stated future goal is to retain the core while changing the LLM API and UI. These are recommendations for a later task, not changes made by this audit.

| Category | Files | Reason |
|---|---|---|
| Files that should remain untouched if interfaces are preserved | `src/indexing.py`, `src/embeddings.py`, `src/store.py`, `src/filters.py`, `src/rag.py`, `src/learning.py`, `src/schemas.py`, `src/export.py`, `src/prompts/*` | They provide the current ingestion, retrieval, learning, schema, export, and prompt contracts. |
| Likely LLM API change | `src/llm.py`; possibly `src/config.py`, `requirements.txt` | `invoke_llm(prompt)->str` is the sole LLM call boundary; provider/model/key settings and SDK dependency live here. |
| Likely Streamlit UI change | `app.py`, `static/style.css`, `static/aivn_logo.png`; `README.md`, `requirements.txt` | Current app is Gradio, so a Streamlit UI would replace/rework its entry point and presentation/deployment dependency metadata. |
| Possible config-only changes | `src/config.py` defaults/validation or environment overrides | Only if the chosen future API needs a different model, credential, or URL. There is no current API URL setting. |

The future UI can use the existing core Python functions directly; a separate REST layer is not present or required by the current architecture. Preserve the core call signatures if the later change is meant to be minimal.

## 22. Suggested Next Steps

1. Confirm deployment working directory, Python/dependency environment, storage permissions, and which Gemini credential/model will be used; inspect the relevant environment overrides without committing a key.
2. Plan and implement the intended LLM API change at `src/llm.py` and its configuration/dependency boundary.
3. In a later authorized task, run a small core smoke test covering one PDF index, one retrieval, and one generation call.
4. Replace/rework the Gradio `app.py` for the intended Streamlit UI while continuing to call the same core functions.
5. Run a final demo covering upload, Q&A, summary, quiz, flashcards, citations, and downloads.

None of these next steps was executed during this audit.
