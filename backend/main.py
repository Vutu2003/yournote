"""HTTP transport over the existing RAG core. Run from project/ with one worker."""

import logging
import sys
import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from backend.api.routes import chat, documents, exports, learning
from backend.schemas.api import HealthResponse
from backend.services import core_adapter

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await run_in_threadpool(core_adapter.close)


app = FastAPI(
    title="Research Notebook API", version="0.2.0", lifespan=lifespan,
    description="Local React transport for the existing PDF RAG core. Explicit PDF selection is required. Use one worker for embedded Qdrant; run from project/. Gemini credentials stay on the server.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
    expose_headers=["Content-Disposition"],
)


@app.exception_handler(RequestValidationError)
async def invalid_request(request, exc: RequestValidationError):
    # Default validation errors echo raw input. Publish schema issues only.
    issues = [{"loc": list(e["loc"]), "msg": e["msg"], "type": e["type"]} for e in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": issues})


@app.exception_handler(core_adapter.AdapterError)
async def adapter_error(request, exc: core_adapter.AdapterError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(Exception)
async def core_error(request, exc: Exception):
    details = "".join(traceback.format_exception(exc))
    config = sys.modules.get("src.config")
    key = getattr(getattr(config, "settings", None), "gemini_api_key", None)
    if key:
        details = details.replace(key, "[redacted]")
    logger.error("Core request failed\n%s", details)
    return JSONResponse(status_code=500, content={"detail": "Unable to complete the operation. Please try again."})


@app.get("/api/health", response_model=HealthResponse, tags=["Health"], summary="Check the HTTP service without loading AI")
def health() -> HealthResponse:
    return HealthResponse()


for router in (documents.router, chat.router, learning.router, exports.router):
    app.include_router(router)
