"""Document analysis service.

PDFs → text via pypdf.
Images → described via Groq vision (llama-3.2-90b-vision-preview).
Text summarisation → via Groq chat.
"""
from __future__ import annotations

import base64
from pathlib import Path

from groq import Groq
from pypdf import PdfReader

from app.core.config import settings
from app.core.logging import get_logger

log = get_logger(__name__)


def _client() -> Groq:
    return Groq(api_key=settings.GROQ_API_KEY)


def extract_text_from_pdf(path: str | Path) -> str:
    """Return all text from a PDF, page by page."""
    reader = PdfReader(str(path))
    pages = []
    for i, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception as e:  # noqa: BLE001
            log.warning("PDF page %d extraction failed: %s", i, e)
            text = ""
        pages.append(f"[Page {i}]\n{text.strip()}")
    return "\n\n".join(pages).strip()


def analyse_image(path: str | Path, instruction: str | None = None) -> str:
    """Send an image to Groq vision and return analysis as plain text."""
    path = Path(path)
    image_bytes = path.read_bytes()
    mime = _guess_mime(path.suffix.lower())
    b64 = base64.b64encode(image_bytes).decode()

    prompt = instruction or (
        "You are a healthcare document analyst. Analyse this image. "
        "If it is a prescription, extract: patient name, medicines (name, dosage, "
        "frequency, duration), doctor name, date. "
        "If it is a lab report, extract: test names, values, normal ranges, anything abnormal. "
        "If it is something else, describe it briefly. "
        "Return clean readable plain text — no markdown headers."
    )

    response = _client().chat.completions.create(
        model="llama-3.2-90b-vision-preview",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
                    {"type": "text", "text": prompt},
                ],
            }
        ],
        max_tokens=1024,
    )
    return (response.choices[0].message.content or "").strip()


def summarise_text(text: str, instruction: str | None = None) -> str:
    """Summarise a block of text using Groq."""
    prompt = instruction or (
        "Summarise this healthcare document. If it's a lab report, list test results "
        "and flag anything outside normal range. If it's a prescription, list medicines "
        "with dosage. Keep it under 200 words, plain text."
    )

    response = _client().chat.completions.create(
        model=settings.LLM_MODEL,
        messages=[
            {"role": "user", "content": f"{prompt}\n\n---\n\n{text[:30000]}"}
        ],
        max_tokens=512,
    )
    return (response.choices[0].message.content or "").strip()


def _guess_mime(ext: str) -> str:
    return {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }.get(ext, "image/jpeg")