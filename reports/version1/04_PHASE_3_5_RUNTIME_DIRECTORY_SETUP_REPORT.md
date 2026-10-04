# Phase 3.5 — Runtime Directory Setup Report

Setup date: 2026-09-30.

## Project Root

/home/vutu/Desktop/rag_notebooklm/project

The current Pydantic configuration loads an optional .env and gives data_dir the default relative path data and storage_dir the default relative path storage/qdrant (src/config.py:16-25). A read-only settings check from the project root resolved those paths to the absolute paths below. No .env contents or API key values were displayed.

## Directory Configuration Discovered

The paths below are relative to the project root unless shown as absolute. “Tracked” refers to files in the directory, because Git does not track empty directories.

### A. Source / tracked or existing report output

| Path | Purpose | Source/config reference | Git state | Existed before | Exists after |
|---|---|---|---|---|---|
| src/ | Application Python modules | Imports throughout app.py | Tracked source files | YES | YES |
| src/prompts/ | Jinja prompt templates | src/rag.py:16, src/rag.py:69-72 | Tracked source files | YES | YES |
| static/ | CSS and logo loaded by the UI | app.py:40, app.py:285-288 | Tracked assets | YES | YES |
| reports/ | Audit/setup/smoke-test reports | Requested report output; no runtime code dependency | Present, not ignored; current report files are untracked | YES | YES |

### B. Local runtime

| Path | Purpose | Source/config reference | Git state | Existed before | Exists after |
|---|---|---|---|---|---|
| data/ | Source/uploaded PDFs; top-level PDF discovery | src/config.py:23; src/indexing.py:65-69, src/indexing.py:158-161 | Ignored by .gitignore | NO | YES, empty |
| storage/ | Parent of configured Qdrant directory | src/config.py:24; src/store.py:35-36 | Ignored by .gitignore | NO | YES |
| storage/qdrant/ | Embedded Qdrant disk storage | src/config.py:24; src/store.py:32-36 | Ignored through storage/ | NO | YES, empty |

The application can create data/ on upload and storage/qdrant/ when opening the Qdrant client, but the directories were prepared now so the user can place PDFs locally and the configured storage path exists. No Qdrant client was opened, and no collection or vector was written. No existing data was moved, overwritten, or deleted.

### C. Optional / generated

| Path | Purpose | Source/config reference | Git state | Existed before | Exists after |
|---|---|---|---|---|---|
| exports/ | Markdown downloads produced by UI callbacks | app.py:251-257; src/export.py:156-161 | Ignored by .gitignore | NO | NO; created on demand, so not created here |
| .venv/ | Local Python environment | Environment setup, not application source | Ignored by .gitignore | YES | YES |
| __pycache__/ | Python bytecode cache, wherever generated | Python runtime; .gitignore:1 | Ignored | Not relevant to preparation | Not manually created |
| .pytest_cache/ | Optional test cache | Test tooling; .gitignore:8 | Ignored | Not relevant to preparation | Not manually created |

## Final Runtime Structure

```text
project/
├── data/                 # empty; place intended PDFs here
├── reports/              # existing reports, including this report
├── src/
│   └── prompts/
├── static/
└── storage/
    └── qdrant/           # empty; no collection initialized
```

Only these relevant directories are shown. The project .venv and any caches are omitted from the tree.

## PDF Input Directory

Place Phase 4 PDF files here:

/home/vutu/Desktop/rag_notebooklm/project/data

The current discover_pdfs() implementation scans PDF files directly in this directory and does not recurse into subdirectories (src/indexing.py:65-69). No PDF was downloaded, copied, moved, or ingested in this phase.

## Qdrant Storage Directory

/home/vutu/Desktop/rag_notebooklm/project/storage/qdrant

This is the effective local path from settings.storage_dir when running from the project root. It exists and is empty. No Qdrant client was initialized.

## Git Ignore Status

.gitignore already ignores data/, storage/ (including storage/qdrant/), exports/, .env, .venv/, __pycache__/, and .pytest_cache/. Each rule was confirmed with git check-ignore. No .gitignore change was made in this phase.

Empty ignored runtime directories are not stored by Git. A fresh clone therefore does not recreate data/ or storage/qdrant/ automatically; local directory preparation is expected.

## Source Changes

NONE. No application source, dependency, configuration, prompt, or static asset file was edited. The only new project file from this phase is this report. The created directories are empty and ignored.

## Result

READY

The configured PDF input and local Qdrant storage directory structure now exists. Both runtime locations were empty at verification. No indexing, model load, Gemini call, retrieval, or UI launch occurred.

## Recommended Next Step

The user manually places the intended PDF files directly in /home/vutu/Desktop/rag_notebooklm/project/data. After that, proceed separately to PHASE 4 — Retrieval + End-to-End RAG Q&A Smoke Test. Phase 4 was not started here.
