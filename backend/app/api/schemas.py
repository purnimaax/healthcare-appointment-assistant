"""Pydantic schemas used in API request/response payloads."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ----- Chat ----------------------------------------------------------------
class ChatRequest(BaseModel):
    """Incoming chat message."""
    session_id: str = Field(..., description="Stable per-browser session ID.")
    message: str = Field(..., min_length=1, max_length=4000)


class ToolCallEvent(BaseModel):
    """A single tool invocation, surfaced to the UI."""
    tool: str
    label: str
    status: str  # running | done | error
    args: dict[str, Any] = {}
    result: Optional[dict[str, Any]] = None


class ChatResponse(BaseModel):
    """Full (non-streaming) chat response."""
    session_id: str
    reply: str
    intent: Optional[str] = None
    language: Optional[str] = None
    tool_calls: list[ToolCallEvent] = []


# ----- Appointments --------------------------------------------------------
class FetchSlotsRequest(BaseModel):
    department: str
    appointment_date: str = Field(..., description="YYYY-MM-DD")
    doctor: Optional[str] = None


class BookAppointmentRequest(BaseModel):
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    department: str
    appointment_date: str = Field(..., description="YYYY-MM-DD")
    time_slot: str = Field(..., description="HH:MM, 24h")
    doctor: Optional[str] = None
    notes: Optional[str] = None


class ModifyAppointmentRequest(BaseModel):
    new_date: Optional[str] = None
    new_time_slot: Optional[str] = None


class AppointmentOut(BaseModel):
    appointment_id: int
    department: str
    doctor: str
    date: str
    time: str
    status: str
    notes: Optional[str] = None


# ----- Documents -----------------------------------------------------------
class DocumentUploadResponse(BaseModel):
    filename: str
    type: str  # 'pdf' | 'image'
    chunks_indexed: int
    extracted_text_preview: str
    summary: Optional[str] = None
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
