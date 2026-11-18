"""SQLite notebook storage; indexed PDFs remain in the existing vector store."""

from contextlib import closing, contextmanager
from datetime import datetime, timezone
import json
import sqlite3
from threading import RLock
from uuid import uuid4

from backend.schemas.notebooks import Notebook, NotebookCreate, NotebookInfo, NotebookUpdate, WorkspaceState
from backend.services.core_adapter import AdapterError, _core_lock
from src.config import settings

_lock = RLock()


def _database_path():
    return settings.storage_dir.parent / "notebooks.sqlite"


def _now():
    return datetime.now(timezone.utc).isoformat()


def _insert(connection, title, icon, state):
    identifier, timestamp = str(uuid4()), _now()
    connection.execute(
        "INSERT INTO notebooks VALUES (?, ?, ?, ?, ?, ?)",
        (identifier, title, icon, timestamp, timestamp, state.model_dump_json()),
    )
    return identifier


@contextmanager
def _database():
    with _lock:
        path = _database_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(path, timeout=10)) as connection:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("CREATE TABLE IF NOT EXISTS notebooks (id TEXT PRIMARY KEY, title TEXT NOT NULL, icon TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL, state TEXT NOT NULL)")
            connection.execute("CREATE TABLE IF NOT EXISTS pdf_highlights (id TEXT PRIMARY KEY, notebook_id TEXT NOT NULL REFERENCES notebooks(id) ON DELETE CASCADE, document_id TEXT NOT NULL, document_version TEXT NOT NULL, page INTEGER NOT NULL, text TEXT NOT NULL, rects TEXT NOT NULL, created_at TEXT NOT NULL)")
            connection.execute("CREATE INDEX IF NOT EXISTS pdf_highlights_document ON pdf_highlights (notebook_id, document_id, document_version)")
            connection.execute("CREATE TABLE IF NOT EXISTS migrations (name TEXT PRIMARY KEY)")
            if not connection.execute("SELECT 1 FROM migrations WHERE name = 'legacy_sources'").fetchone():
                from src.store import list_documents

                with _core_lock:
                    filenames = [str(doc["filename"]) for doc in list_documents()]
                if filenames:
                    _insert(connection, "Tài liệu nghiên cứu", "📚", WorkspaceState(document_filenames=filenames, selected=filenames))
                connection.execute("INSERT INTO migrations VALUES ('legacy_sources')")
            yield connection
            connection.commit()


def _notebook(row) -> Notebook:
    if row is None:
        raise AdapterError(404, "Notebook not found.")
    state = WorkspaceState.model_validate(json.loads(row["state"]))
    return Notebook(
        id=row["id"], title=row["title"], icon=row["icon"],
        created_at=row["created_at"], updated_at=row["updated_at"],
        source_count=len(state.document_filenames), chat_count=len(state.chat), state=state,
    )


def list_notebooks() -> list[NotebookInfo]:
    with _database() as connection:
        return [NotebookInfo.model_validate(_notebook(row).model_dump(exclude={"state"})) for row in connection.execute("SELECT * FROM notebooks ORDER BY updated_at DESC, id")]


def get_notebook(identifier: str) -> Notebook:
    with _database() as connection:
        return _notebook(connection.execute("SELECT * FROM notebooks WHERE id = ?", (identifier,)).fetchone())


def create_notebook(request: NotebookCreate) -> Notebook:
    with _database() as connection:
        identifier = _insert(connection, request.title, request.icon, WorkspaceState())
        return _notebook(connection.execute("SELECT * FROM notebooks WHERE id = ?", (identifier,)).fetchone())


def update_notebook(identifier: str, request: NotebookUpdate) -> Notebook:
    with _database() as connection:
        result = connection.execute(
            "UPDATE notebooks SET title = ?, icon = ?, updated_at = ?, state = ? WHERE id = ?",
            (request.title, request.icon, _now(), request.state.model_dump_json(), identifier),
        )
        if result.rowcount == 0:
            raise AdapterError(404, "Notebook not found.")
        return _notebook(connection.execute("SELECT * FROM notebooks WHERE id = ?", (identifier,)).fetchone())


def delete_notebook(identifier: str) -> None:
    with _database() as connection:
        if connection.execute("DELETE FROM notebooks WHERE id = ?", (identifier,)).rowcount == 0:
            raise AdapterError(404, "Notebook not found.")


def reset_notebook(identifier: str) -> Notebook:
    """Clear one workspace atomically, retaining its identity and shared PDFs."""
    with _database() as connection:
        result = connection.execute(
            "UPDATE notebooks SET state = ?, updated_at = ? WHERE id = ?",
            (WorkspaceState().model_dump_json(), _now(), identifier),
        )
        if result.rowcount == 0:
            raise AdapterError(404, "Notebook not found.")
        connection.execute("DELETE FROM pdf_highlights WHERE notebook_id = ?", (identifier,))
        return _notebook(connection.execute("SELECT * FROM notebooks WHERE id = ?", (identifier,)).fetchone())
