"""Serve both reading conditions with real YourNote APIs and isolated data."""

import argparse
import json
import os
from pathlib import Path
import socket

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[1]


def prepare(root):
    import torch
    from backend.schemas.notebooks import NotebookCreate, NotebookUpdate, WorkspaceState
    from backend.services.notebooks import create_notebook, update_notebook
    from evaluation.phase09 import load_scenarios
    from evaluation.phase07.__main__ import load_fixture, file_sha256, materialize
    from src.config import settings
    from src.indexing import save_and_ingest_document

    assert settings.data_dir == root / "data" and settings.storage_dir == root / "storage/qdrant"
    assert settings.chatgpt_runtime_dir == root / "chatgpt" and not settings.gemini_api_key
    torch.set_num_threads(2)
    scenarios = load_scenarios()
    fixture, policy = load_fixture()
    selected = [scenarios["pdf"], scenarios["distractor"]]
    inputs = {**fixture, "sources": [source for source in fixture["sources"] if source["id"] in selected]}
    paths = materialize(root / "materials", inputs, policy)
    documents = {key: save_and_ingest_document(paths[key].read_bytes(), paths[key].name) for key in selected}
    target, distractor = (documents[key] for key in selected)
    aliases = {target["filename"]: scenarios["scope_title"], distractor["filename"]: scenarios["distractor_title"]}

    saved_path = PROJECT / "evaluation/phase08/artifacts/inference.json"
    saved = json.loads(saved_path.read_text())
    condition_data = {}
    assignments = []
    for group, runs in enumerate(scenarios["assignments"], 1):
        sessions = []
        for order, (mode, set_id) in enumerate(runs, 1):
            trial_id = f"I{group:02d}-{order}"
            task = scenarios["tasks"][set_id]
            row = next(row for row in saved["rows"] if row["case_id"] == task["case_id"] and
                       row["retriever"] == "hybrid" and row["status"] == "completed")
            assert len(row["citations"]) == 1
            citation = row["citations"][0]
            assert (citation["filename"], citation["document_id"], citation["document_version"], citation["page"]) == (
                target["filename"], target["document_id"], target["document_version"], task["page"])
            generation = {
                "provider": saved["provider"], "requested_model": saved["model_requested"], "model": row["actual_model"],
                "actual_models": [row["actual_model"]] if row["actual_model"] else [], "created_at": saved["observed_utc"],
                "request_id": row["case_id"], "source_versions": {target["filename"]: target["document_version"]},
                "source_filenames": [target["filename"]], "pages": [task["page"]], "calls": row["model_calls"],
                "duration_seconds": row["response_seconds"], "usage": row["usage"],
            }
            title = f"Phase 09 · {trial_id} · Thẻ {set_id}"
            if mode == "yournote":
                notebook = create_notebook(NotebookCreate(title=title))
                state = WorkspaceState(
                    document_filenames=list(aliases), source_names=aliases, selected=list(aliases),
                    chat=[{"question": row["question"], "answer": row["answer"], "citations": [citation],
                           "generation": {**generation, "notebook_id": notebook.id}}],
                )
                update_notebook(notebook.id, NotebookUpdate(title=title, state=state))
                notebook_id = notebook.id
            else:
                notebook_id = None
            for_trial = {
                **task, "mode": mode, "set": set_id, "trial_id": trial_id, "order": order, "sequence": group,
                "notebook_id": notebook_id, "notebook_title": title, "question": row["question"],
                "answer": row["answer"], "citation": citation, "model": row["actual_model"],
                "source_title": scenarios["scope_title"], "distractor_title": scenarios["distractor_title"],
                "pdf_url": "/phase09/original.pdf", "phase08_conditions_sha256": saved["plan_sha256"],
                "pdf_page_count": len(next(s for s in inputs["sources"] if s["id"] == selected[0])["pages"]),
            }
            sessions.append(for_trial)
            condition_data[trial_id] = for_trial
        assignments.append(sessions)
    return {
        "runs": assignments, "cases": condition_data, "pdf": paths[scenarios["pdf"]], "docs": documents,
        "source_sha256": {key: file_sha256(path) for key, path in paths.items()},
        "phase08_answers_sha256": file_sha256(saved_path),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    root = args.directory.resolve()
    # The launcher creates a fresh directory. Never accept existing runtime storage.
    assert root.is_dir() and not any(root.iterdir()), "Use a dedicated empty directory."
    os.environ.update(
        RAG_DATA_DIR=str(root / "data"), RAG_STORAGE_DIR=str(root / "storage/qdrant"),
        RAG_CHATGPT_RUNTIME_DIR=str(root / "chatgpt"), GEMINI_API_KEY="",
        HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1",
    )
    from src.store import close_client
    try:
        data = prepare(root)
    except Exception:
        close_client()
        raise

    import uvicorn
    from backend.main import app as yournote
    from starlette.responses import FileResponse, JSONResponse
    from starlette.routing import Route
    from starlette.staticfiles import StaticFiles
    from starlette.applications import Starlette

    async def case_data(request):
        key = request.path_params["trial"]
        case = data["cases"].get(key)
        public = ("question", "answer", "page", "model", "source_title", "distractor_title", "pdf_url", "pdf_page_count")
        return JSONResponse({key: case[key] for key in public}) if case else JSONResponse({}, status_code=404)

    async def document(_):
        return FileResponse(data["pdf"], media_type="application/pdf")

    async def comparison(_):
        return FileResponse(ROOT / "comparison.html", media_type="text/html")

    async def pdfjs(request):
        file = request.path_params["file"]
        if file not in {"pdf.min.mjs", "pdf.worker.min.mjs"}:
            return JSONResponse({}, status_code=404)
        return FileResponse(PROJECT / "frontend/node_modules/pdfjs-dist/build" / file, media_type="text/javascript")

    (root / "dist").mkdir()
    # Vite fills the temporary dist directory after the listener reports its port.
    site = Starlette(routes=[
        Route("/phase09/case/{trial}", case_data), Route("/phase09/original.pdf", document),
        Route("/phase09/compare", comparison), Route("/phase09/pdfjs/{file}", pdfjs),
    ])
    site.mount("/", StaticFiles(directory=root / "dist", html=True))

    async def application(scope, receive, send):
        if scope["type"] == "lifespan" or scope.get("path", "").startswith("/api/"):
            if scope.get("path") == "/api/ai/tasks" and scope["method"] == "POST":
                await JSONResponse({"detail": "Phase 09 uses saved responses."}, status_code=403)(scope, receive, send)
                return
            await yournote(scope, receive, send)
        else:
            await site(scope, receive, send)

    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen(128)
        info = {key: data[key] for key in ("runs", "docs", "source_sha256", "phase08_answers_sha256")}
        info["origin"] = f"http://127.0.0.1:{listener.getsockname()[1]}"
        print(json.dumps(info, ensure_ascii=False), flush=True)
        uvicorn.Server(uvicorn.Config(application, log_level="warning")).run(sockets=[listener])


if __name__ == "__main__":
    main()
