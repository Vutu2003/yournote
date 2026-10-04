# Research Notebook frontend scaffold

Run from the project root:

```bash
./scripts/dev_backend.sh
# In a second terminal:
./scripts/dev_frontend.sh
```

Open http://127.0.0.1:5173. The screen only checks `GET /api/health`.

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

`package-lock.json` records the installed dependency versions. Sources, Chat,
Studio, and their API endpoints are reserved for a later phase.
