from fastapi import APIRouter, Response

from backend.schemas.api import ERROR_RESPONSES, ExportRequest
from backend.services import core_adapter

router = APIRouter(prefix="/api", tags=["Export"], responses=ERROR_RESPONSES)


@router.post("/export", summary="Download canonical Markdown from a validated result",
             description="Send feature and its result. This validates structure and renders client-provided data; it does not re-check factuality or call Gemini. No client paths or server persistence.",
             response_class=Response,
             responses={200: {"description": "Markdown attachment", "content": {"text/markdown": {"schema": {"type": "string"}}}}})
def export_markdown(request: ExportRequest):
    return Response(
        content=core_adapter.markdown(request), media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{request.feature}.md"'},
    )
