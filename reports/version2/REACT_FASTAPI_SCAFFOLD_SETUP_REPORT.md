# React + FastAPI Scaffold Setup Report

Phase: **9A — Project Scaffolding and Tool Setup**. Date: **2026-10-04**.

## Phase Result

**PASS.** FastAPI health, the React development page, the production build, browser connectivity, CORS, and existing-file integrity were verified. All test services were stopped afterward. No commit or push was made.

## Architecture

Target architecture: **Browser → React/TypeScript/Vite → FastAPI → Existing Python RAG Core**.

In this scaffold, React calls only `GET /api/health`. FastAPI does not yet import or invoke the core. Business adapters and endpoints belong to Phase 9B. **No SQL database added.** The existing Gradio implementation remains the fallback.

## Existing Core Protection

- A SHA-256 snapshot before and after the work matched for all **30 protected files** under `src/`, `data/`, `storage/`, plus `app.py`, root `requirements.txt`, and `.env`. No protected file was added, removed, or changed.
- `git diff -- src/ requirements.txt` was empty. `app.py` and `static/style.css` already had Phase 8 edits before this task; those edits were preserved. The `app.py` hash did not change during Phase 9A.
- No Gradio launch, PDF upload, reindex, vector deletion, Qdrant client opening, embedding inference, or Gemini invocation was performed.
- Importing `backend.main` loaded none of `src`, `sentence_transformers`, `qdrant_client`, or `google.genai` into `sys.modules`.

## System Tooling

| Tool | Observed version / location |
|---|---|
| Project Python | 3.12.10; `.venv/bin/python` |
| Activated `which python` | `/home/vutu/Desktop/rag_notebooklm/project/.venv/bin/python` |
| Project pip | 26.2.1 |
| System Python | 3.14.4 via `/usr/bin/python3`; left unchanged |
| Node.js | v24.21.0, LTS Krypton |
| npm / npx | 11.19.0 / 11.19.0 |
| create-vite | 9.2.1 |
| Vite | 8.3.2 |
| Git | 2.53.0 |
| curl | Not installed; Python `urllib.request` used for HTTP verification |

Node/npm/npx were absent from PATH, and no existing nvm installation was found. The official Linux x64 Node archive was downloaded, checked against its [official SHA-256 manifest](https://nodejs.org/dist/v24.21.0/SHASUMS256.txt), and extracted to `.tools/node-v24.21.0-linux-x64`; `.tools/node` is a relative symlink to it. This is a project-local installation, with no sudo, global npm installation, or shell-profile change. `.tools/` is ignored.

The React TypeScript scaffold used the [documented Vite CLI](https://vite.dev/guide/): `npm create vite@latest frontend -- --template react-ts --no-interactive`. The selected Node runtime meets the documented Vite Node minimum.

## Backend Scaffold

Created `backend/main.py`, package markers for `backend/`, `backend/api/`, `backend/api/routes/`, `backend/schemas/`, and `backend/services/`, and `backend/requirements-api.txt`.

| API dependency | Exact installed version |
|---|---|
| FastAPI | 0.142.1 |
| Uvicorn | 0.54.0 |
| python-multipart | 0.0.32 |

All three packages were already installed in the existing `.venv`. **No Python package was installed, upgraded, or reinstalled.** `pip check` passed. `requirements-api.txt` pins these API-layer dependencies without duplicating the root RAG dependency list. Uvicorn's optional `standard` extras were not added.

Application title: **Research Notebook API**. The only custom endpoint is `GET /api/health`, returning exactly `{"status":"ok"}`. It is independent of environment credentials, models, PDFs, and vector storage.

## Backend Verification

The following command started successfully:

```bash
.venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

| Check | Result |
|---|---|
| `/api/health` | HTTP 200; exact expected JSON |
| `/docs` | HTTP 200 |
| `/openapi.json` | HTTP 200; only `/api/health` in the custom paths |
| CORS GET and OPTIONS from `http://localhost:5173` | PASS |
| CORS GET and OPTIONS from `http://127.0.0.1:5173` | PASS |
| Unlisted origin | No `Access-Control-Allow-Origin` header |

`CORSMiddleware` has those two explicit origins, `allow_credentials=False`, `allow_methods=["GET"]`, and `allow_headers=["Content-Type"]`. No wildcard origin is configured.

## Frontend Scaffold

| Dependency | Exact installed version |
|---|---|
| React | 19.3.0 |
| React DOM | 19.3.0 |
| TypeScript | 6.0.3 |
| Vite | 8.3.2 |
| `@vitejs/plugin-react` | 6.1.1 |
| Oxlint, from the standard template | 1.86.0 |

`npm install` completed: 27 packages added; audit reported zero vulnerabilities. `package-lock.json` records resolved versions. No UI framework, Axios, Tailwind, monorepo manager, or extra application dependency was added.

The default logos, hero, counter, demo instructions, and decorative SVG files were removed. The shell contains only the Research Notebook heading, frontend-ready text, and backend connectivity status. An empty data favicon prevents a browser request for a missing default favicon. API/type/style modules and empty Sources/Chat/Studio/components directories are prepared for later work.

`package.json` retains `dev`, `build`, `preview`, and the template's `lint` scripts. `npm run build` passed TypeScript compilation and Vite production bundling; the final build had no toolchain warnings. `npm run lint` passed.

## Frontend Connectivity

- `VITE_API_BASE_URL=http://127.0.0.1:8000` is the example configuration and the client's local fallback. The development verification also supplied this value explicitly in the Vite process environment.
- `frontend/src/api/client.ts` uses browser `fetch`, validates the health JSON shape, and supports an abort signal. It contains no RAG request or direct provider request.
- Headless Chrome opened `http://127.0.0.1:5173/` and rendered **“Backend status: connected”**. The cross-origin `/api/health` response was captured as HTTP 200. No fatal console errors or resource errors remained after the favicon correction; no logo images were present.
- Evidence: [frontend connected screenshot](PHASE_9A_FRONTEND_CONNECTED.png).
- FastAPI, Vite, and the isolated Chrome session were stopped. Ports **8000, 5173, and 9223** had no listener afterward. An initial bind-only cleanup probe encountered TCP TIME_WAIT; listener inspection and connection checks confirmed the services were stopped.

## Directory Structure

```text
project/
├── backend/
│   ├── __init__.py
│   ├── main.py
│   ├── requirements-api.txt
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes/__init__.py
│   ├── schemas/__init__.py
│   └── services/__init__.py
├── frontend/
│   ├── .env.example
│   ├── .gitignore
│   ├── .oxlintrc.json
│   ├── README.md
│   ├── package.json
│   ├── package-lock.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── tsconfig.app.json
│   ├── tsconfig.node.json
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── api/client.ts
│       ├── types/api.ts
│       ├── styles/index.css
│       ├── components/
│       └── features/
│           ├── sources/
│           ├── chat/
│           └── studio/
├── src/                         # existing core
├── data/                        # existing PDFs
├── storage/                     # existing local runtime data
├── reports/
│   └── version2/
│       ├── REACT_FASTAPI_SCAFFOLD_SETUP_REPORT.md
│       └── PHASE_9A_FRONTEND_CONNECTED.png
├── scripts/
│   ├── start.sh                 # existing Gradio launcher
│   ├── stop.sh                  # existing Gradio stopper
│   ├── dev_backend.sh
│   └── dev_frontend.sh
├── app.py                       # existing Gradio fallback
├── requirements.txt
└── .gitignore
```

Installed runtimes, `.venv`, `node_modules`, `dist`, Git metadata, caches, and Qdrant internals are omitted above. Empty feature directories contain `.gitkeep` files only.

## Git Ignore Changes

Only these root entries were appended:

```gitignore
.tools/
frontend/node_modules/
frontend/dist/
frontend/.env.local
frontend/.env.*.local
```

Existing `.venv/`, `.env`, `data/`, `storage/`, `exports/`, `__pycache__/`, and `.pytest_cache/` ignores were preserved. The existing `.env` pattern also covers `frontend/.env`. `frontend/.env.example` remains trackable. The generated frontend `.gitignore` retains the template's normal logs, build, dependency, and editor exclusions.

## Files Added

- Backend scaffold and API-only dependency pins listed in the tree.
- Standard Vite/React/TypeScript package, lock, compiler, and lint configuration.
- Minimal React shell, API client, health response type, neutral stylesheet, public environment example, and frontend README.
- Executable `scripts/dev_backend.sh` and `scripts/dev_frontend.sh`; both passed `bash -n`. The frontend script uses the project-local Node runtime when present. Both scripts resolve the project directory from their own location.
- This report and the browser screenshot under `reports/version2/`.

## Files Modified

Existing repository file changed in Phase 9A: **`.gitignore` only**. Existing core files: **NONE**. `app.py`, root `requirements.txt`, and the existing Gradio scripts were unchanged. Files customized within the newly generated `frontend/` are part of this phase's new scaffold.

`git status` still shows the earlier Phase 8 `app.py`/CSS changes and untracked reports/scripts. They were already present before Phase 9A. `git diff --check` passed. No commit or push was made.

## Security Check

- The existing Gemini credential remains server-side in the protected root configuration; FastAPI health does not read it.
- An exact-value scan against the configured Gemini key passed for 30 generated frontend/backend files, including frontend build output and excluding third-party `node_modules` and Python caches. No secret was printed.
- `frontend/.env.example` contains only a public API base URL. No actual frontend secret environment file was created.
- The API's health JSON contains neither secrets nor filesystem paths or configuration details. Only loopback listeners were started, with no public sharing.

## Result

**PASS**: FastAPI health works; the React development page works; the production build works; the browser calls the backend successfully through CORS; and all protected project files match their initial hashes.

Setup notices: npm advertised an available npm major update, which was not installed; pip reported a disabled cache under the execution sandbox while `pip check` passed. Chrome emitted background-service messages in its process output, while the verified application console had no errors. There are no outstanding scaffold blockers.

To run the development scaffold, use two terminals from the project root:

```bash
./scripts/dev_backend.sh
./scripts/dev_frontend.sh
```

Open `http://127.0.0.1:5173/`. For a production build from the current workspace:

```bash
export PATH="$PWD/.tools/node/bin:$PATH"
cd frontend
npm run build
```

## Recommended Next Step

**PHASE 9B — FastAPI API Contract and Endpoint Implementation**: define HTTP contracts and wrap the validated core for documents, upload, chat, summary, quiz, flashcards, and exports. None of those business endpoints were implemented in Phase 9A.
