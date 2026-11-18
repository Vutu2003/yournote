"""Notebook home and independent, saved workspaces."""

from fastapi import APIRouter, Response

from backend.schemas.api import ERROR_RESPONSES
from backend.schemas.notebooks import Notebook, NotebookCreate, NotebookReset, NotebookUpdate, NotebooksResponse
from backend.services import notebooks

router = APIRouter(prefix="/api/notebooks", tags=["Notebooks"], responses=ERROR_RESPONSES)


@router.get("", response_model=NotebooksResponse, summary="List saved notebooks")
def list_notebooks():
    return NotebooksResponse(notebooks=notebooks.list_notebooks())


@router.post("", response_model=Notebook, status_code=201, summary="Create an empty notebook")
def create_notebook(request: NotebookCreate):
    return notebooks.create_notebook(request)


@router.get("/{identifier}", response_model=Notebook, summary="Open a saved notebook")
def get_notebook(identifier: str):
    return notebooks.get_notebook(identifier)


@router.put("/{identifier}", response_model=Notebook, summary="Save notebook metadata and workspace")
def update_notebook(identifier: str, request: NotebookUpdate):
    return notebooks.update_notebook(identifier, request)


@router.delete("/{identifier}", status_code=204, summary="Delete a notebook, retaining library PDFs")
def delete_notebook(identifier: str):
    notebooks.delete_notebook(identifier)
    return Response(status_code=204)


@router.post("/{identifier}/reset", response_model=Notebook, summary="Reset one notebook's content, retaining the notebook and shared PDFs")
def reset_notebook(identifier: str, request: NotebookReset):
    return notebooks.reset_notebook(identifier)
