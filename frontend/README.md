# Research Notebook frontend

Run from the project root:

```bash
./scripts/dev_backend.sh
# In a second terminal:
./scripts/dev_frontend.sh
```

Open http://127.0.0.1:5173. Select indexed PDF sources to use Chat or the
Summary, Quiz, and Flashcards tools in Studio. Page filtering is available
when exactly one PDF is selected. Run one FastAPI worker for embedded Qdrant.

The API base URL defaults to `http://127.0.0.1:8000`. To override it, copy
`.env.example` to `.env.local` and change `VITE_API_BASE_URL`, then restart Vite.
Vite environment values are public: never put Gemini keys or other secrets here.

For this workspace's local Node installation, run from the project root:

```bash
export PATH="$PWD/.tools/node/bin:$PATH"
cd frontend
npm ci
npm run build
npm run preview -- --host 127.0.0.1
```

`package-lock.json` records the installed dependency versions. Generated results
and quiz/card interactions stay in React state until the page reloads. Use
**Tải Markdown** to download a result through the backend export endpoint.
