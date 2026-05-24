"""LangChain tool definitions.

Thin wrappers around the service layer. All the actual logic lives in services/.
Errors are caught and returned as dicts so the LLM can read them and recover
instead of crashing the loop.
"""
from __future__ import annotations

from typing import Optional

from langchain_core.tools import tool

from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.services import appointments as appt_svc
from app.services.rag import get_rag

log = get_logger(__name__)


def _err(e: Exception) -> dict:
    return {"error": str(e), "ok": False}


@tool
def fetch_slots(
    department: str,
    appointment_date: str,
    doctor: Optional[str] = None,
) -> dict:
    """Get available appointment slots for a department/doctor on a date.

    Args:
        department: e.g. "Cardiology", "General Medicine"
        appointment_date: YYYY-MM-DD
        doctor: optional — defaults to first doctor in the department
    """
    db = SessionLocal()
    try:
        return {
            "ok": True,
            **appt_svc.fetch_available_slots(
                db, department=department, appointment_date=appointment_date, doctor=doctor
            ),
        }
    except Exception as e:  # noqa: BLE001
        return _err(e)
    finally:
        db.close()


@tool
def book_appointment(
    name: str,
    department: str,
    appointment_date: str,
    time_slot: str,
    phone: Optional[str] = None,
    email: Optional[str] = None,
    doctor: Optional[str] = None,
    notes: Optional[str] = None,
) -> dict:
    """Book an appointment for a patient.

    Args:
        name: patient's full name
        department: department name
        appointment_date: YYYY-MM-DD
        time_slot: HH:MM (24h), must be a valid clinic slot
        phone: patient phone (at least one of phone/email required)
        email: patient email
        doctor: optional
        notes: optional (e.g. "follow-up", "new patient")
    """
    db = SessionLocal()
    try:
        return {
            "ok": True,
            **appt_svc.book_appointment(
                db,
                name=name, phone=phone, email=email,
                department=department, appointment_date=appointment_date,
                time_slot=time_slot, doctor=doctor, notes=notes,
            ),
        }
    except Exception as e:  # noqa: BLE001
        return _err(e)
    finally:
        db.close()


@tool
def cancel_appointment(appointment_id: int) -> dict:
    """Cancel an appointment by its ID.

    Args:
        appointment_id: the numeric ID from when the appointment was booked
    """
    db = SessionLocal()
    try:
        return {"ok": True, **appt_svc.cancel_appointment(db, appointment_id)}
    except Exception as e:  # noqa: BLE001
        return _err(e)
    finally:
        db.close()


@tool
def modify_appointment(
    appointment_id: int,
    new_date: Optional[str] = None,
    new_time_slot: Optional[str] = None,
) -> dict:
    """Reschedule an appointment to a new date/time.

    Args:
        appointment_id: ID of the appointment to modify
        new_date: new date YYYY-MM-DD (optional)
        new_time_slot: new time HH:MM (optional)
    """
    db = SessionLocal()
    try:
        return {
            "ok": True,
            **appt_svc.modify_appointment(
                db, appointment_id, new_date=new_date, new_time_slot=new_time_slot
            ),
        }
    except Exception as e:  # noqa: BLE001
        return _err(e)
    finally:
        db.close()


@tool
def retrieve_appointments(
    phone: Optional[str] = None,
    email: Optional[str] = None,
    include_cancelled: bool = False,
) -> dict:
    """Look up a patient's appointments by phone or email.

    Args:
        phone: patient's phone number
        email: patient's email
        include_cancelled: set to true to include cancelled ones
    """
    db = SessionLocal()
    try:
        appts = appt_svc.retrieve_appointments(
            db, phone=phone, email=email, include_cancelled=include_cancelled
        )
        return {"ok": True, "appointments": appts, "count": len(appts)}
    except Exception as e:  # noqa: BLE001
        return _err(e)
    finally:
        db.close()


@tool
def list_departments() -> dict:
    """List all departments and their doctors. Use when the user asks what's available."""
    return {"ok": True, "departments": appt_svc.list_departments_and_doctors()}


@tool
def retrieve_documents(query: str, session_id: Optional[str] = None) -> dict:
    """Search the healthcare KB and any documents the user uploaded this session.

    Use for general health questions: insurance, preparation, FAQs, what departments treat.

    Args:
        query: natural language search query
        session_id: limits user-upload search to the current session
    """
    try:
        results = get_rag().search(query, k=4, session_id=session_id)
        return {
            "ok": True,
            "results": [
                {
                    "text": r["text"],
                    "source": r["metadata"].get("source", "unknown"),
                    "type": r["metadata"].get("type", "kb"),
                }
                for r in results
            ],
            "count": len(results),
        }
    except Exception as e:  # noqa: BLE001
        return _err(e)


APPOINTMENT_TOOLS = [
    fetch_slots,
    book_appointment,
    cancel_appointment,
    modify_appointment,
    retrieve_appointments,
    list_departments,
]

RAG_TOOLS = [retrieve_documents]

ALL_TOOLS = APPOINTMENT_TOOLS + RAG_TOOLS
