from fastapi import APIRouter

from backend.schemas.api import ChatRequest, ChatResponse, ERROR_RESPONSES
from backend.services import core_adapter

router = APIRouter(prefix="/api", tags=["Chat"], responses=ERROR_RESPONSES)


@router.post("/chat", response_model=ChatResponse, summary="Ask a grounded question about selected PDFs",
             description="Uses existing answer() and metadata filters. Source text is returned for deliberate expansion; private chunks and absolute source paths are omitted. No retrieved context returns the core's insufficient-context answer.")
def chat(request: ChatRequest):
    return core_adapter.chat(request)
