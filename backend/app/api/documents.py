"""Document upload endpoint.

Accepts PDFs and images. Extracts text (pypdf for PDFs, Groq vision for images), ingests into the user_uploads vector collection (scoped by
session_id), and returns a summary so the user immediately sees something
useful.
"""
from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.api.schemas import DocumentUploadResponse
from app.core.config import settings
from app.core.logging import get_logger
from app.services import documents as doc_svc
from app.services.rag import get_rag

log = get_logger(__name__)
router = APIRouter(prefix="/api/documents", tags=["documents"])

_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
_PDF_EXTS = {".pdf"}
_MAX_SIZE_MB = 10


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    summary="Upload and analyse a PDF or image",
)
async def upload(
    session_id: str = Form(..., description="Session/thread ID to scope this upload to"),
    file: UploadFile = File(...),
) -> DocumentUploadResponse:
    """Upload a PDF or image, extract content, index for retrieval, return summary."""
    filename = file.filename or "upload"
    ext = Path(filename).suffix.lower()

    if ext not in _IMAGE_EXTS | _PDF_EXTS:
        raise HTTPException(
            400, f"Unsupported file type {ext}. Supported: PDF, JPG, PNG, WEBP, GIF."
        )

    # Persist to disk so vision/parsing libs can read it
    upload_id = uuid.uuid4().hex[:10]
    safe_name = f"{upload_id}_{Path(filename).name}"
    fp = Path(settings.UPLOAD_DIR) / safe_name
    content = await file.read()
    if len(content) > _MAX_SIZE_MB * 1024 * 1024:
        raise HTTPException(400, f"File too large (max {_MAX_SIZE_MB} MB).")
    fp.write_bytes(content)

    doc_type = "pdf" if ext in _PDF_EXTS else "image"

    # Extract text
    try:
        if doc_type == "pdf":
            extracted = doc_svc.extract_text_from_pdf(fp)
        else:
            extracted = doc_svc.analyse_image(fp)
    except Exception as e:  # noqa: BLE001
        log.exception("Extraction failed")
        raise HTTPException(500, f"Failed to extract content: {e}")

    if not extracted.strip():
        raise HTTPException(
            400,
            "Could not extract any content from the file. "
            "If it's a scanned PDF, try uploading the page as an image instead.",
        )

    # Index for retrieval (scoped to session)
    rag = get_rag()
    chunks_indexed = rag.ingest_user_document(
        text=extracted, filename=filename, session_id=session_id,
    )

    # Generate a quick summary so the user has something to look at
    summary = None
    try:
        summary = doc_svc.summarise_text(extracted)
    except Exception as e:  # noqa: BLE001
        log.warning("Summary generation failed (non-fatal): %s", e)

    return DocumentUploadResponse(
        filename=filename,
        type=doc_type,
        chunks_indexed=chunks_indexed,
        extracted_text_preview=extracted[:600],
        summary=summary,
    )
