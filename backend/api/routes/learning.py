from fastapi import APIRouter

from backend.schemas.api import (
    ERROR_RESPONSES, FlashcardsRequest, FlashcardsResponse,
    QuizRequest, QuizResponse, SummaryRequest, SummaryResponse, MindMapRequest, MindMapResponse,
)
from backend.services import core_adapter

router = APIRouter(prefix="/api", tags=["Learning"], responses=ERROR_RESPONSES)


@router.post("/summary", response_model=SummaryResponse, summary="Summarize selected source material",
             description="A non-empty topic maps to core query retrieval. Without topic, all matching chunks are summarized using the unchanged single/map-reduce behavior.")
def summary(request: SummaryRequest):
    return core_adapter.summary(request)


@router.post("/quiz", response_model=QuizResponse, summary="Generate a grounded multiple-choice quiz",
             description="Core may return fewer valid items than requested. Options, answers, explanations and markers are preserved. Checking and navigation belong to React and need no API calls.")
def quiz(request: QuizRequest):
    return core_adapter.quiz(request)


@router.post("/flashcards", response_model=FlashcardsResponse, summary="Generate grounded flashcards",
             description="Core may return fewer cards than requested. Front/back/hint and markers are preserved. Reveal and navigation belong to React.")
def flashcards(request: FlashcardsRequest):
    return core_adapter.flashcards(request)


@router.post("/mindmap", response_model=MindMapResponse, summary="Create a grounded mind map from selected sources")
def mindmap(request: MindMapRequest):
    return core_adapter.mindmap(request)
