"""FastAPI entry point.

uvicorn app.main:app --reload --port 8000
Swagger at http://localhost:8000/docs
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.appointments import router as appointments_router
from app.api.chat import router as chat_router
from app.api.documents import router as documents_router
from app.core.config import settings
from app.core.logging import get_logger, setup_logging
from app.db.session import init_db
from app.services.rag import get_rag


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    log = get_logger("app.startup")

    log.info("Starting Mykare AI Assistant — env=%s", settings.APP_ENV)
    if not settings.GROQ_API_KEY:
        log.warning("GROQ_API_KEY not set — LLM calls will fail. Add it to backend/.env")

    init_db()
    log.info("DB ready at %s", settings.SQLITE_DB_PATH)

    # seed KB on first boot, skip if already done
    if settings.GROQ_API_KEY:
        try:
            added = get_rag().ingest_kb()
            if added:
                log.info("Seeded %d KB chunks", added)
            else:
                log.info("KB up to date — %s", get_rag().kb_stats())
        except Exception as e:  # noqa: BLE001
            log.exception("KB ingestion failed (non-fatal): %s", e)
    else:
        log.warning("Skipping KB ingestion — no GROQ_API_KEY")

    yield
    log.info("Shutting down.")


app = FastAPI(
    title="Mykare AI Healthcare Assistant",
    description=(
        "Multi-agent healthcare front-desk assistant. "
        "Built with LangGraph + Groq + ChromaDB."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)
app.include_router(appointments_router)
app.include_router(documents_router)


@app.get("/", tags=["meta"], summary="Health check")
def root() -> dict:
    return {"status": "ok", "service": "mykare-ai-assistant", "docs": "/docs"}


@app.get("/api/health", tags=["meta"], summary="Detailed health")
def health() -> dict:
    try:
        stats = get_rag().kb_stats()
    except Exception as e:  # noqa: BLE001
        stats = {"error": str(e)}
    return {
        "status": "ok",
        "llm_model": settings.LLM_MODEL,
        "api_key_configured": bool(settings.GROQ_API_KEY),
        "kb_stats": stats,
    }
