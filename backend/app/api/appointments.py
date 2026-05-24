"""REST endpoints for appointment management — same service functions the AI agent uses."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.schemas import (
    AppointmentOut,
    BookAppointmentRequest,
    FetchSlotsRequest,
    ModifyAppointmentRequest,
)
from app.db.session import get_db
from app.services import appointments as svc

router = APIRouter(prefix="/api/appointments", tags=["appointments"])


@router.get("/departments", summary="List departments and doctors")
def list_departments() -> dict:
    return svc.list_departments_and_doctors()


@router.post("/slots", summary="Fetch available slots")
def fetch_slots(req: FetchSlotsRequest, db: Session = Depends(get_db)) -> dict:
    try:
        return svc.fetch_available_slots(
            db,
            department=req.department,
            appointment_date=req.appointment_date,
            doctor=req.doctor,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("", summary="Book a new appointment")
def book(req: BookAppointmentRequest, db: Session = Depends(get_db)) -> dict:
    try:
        return svc.book_appointment(
            db,
            name=req.name, phone=req.phone, email=req.email,
            department=req.department, appointment_date=req.appointment_date,
            time_slot=req.time_slot, doctor=req.doctor, notes=req.notes,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.delete("/{appointment_id}", summary="Cancel an appointment")
def cancel(appointment_id: int, db: Session = Depends(get_db)) -> dict:
    try:
        return svc.cancel_appointment(db, appointment_id)
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.patch("/{appointment_id}", summary="Modify (reschedule) an appointment")
def modify(
    appointment_id: int,
    req: ModifyAppointmentRequest,
    db: Session = Depends(get_db),
) -> dict:
    try:
        return svc.modify_appointment(
            db, appointment_id,
            new_date=req.new_date, new_time_slot=req.new_time_slot,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("", response_model=list[AppointmentOut], summary="List user's appointments")
def list_appointments(
    phone: str | None = Query(None),
    email: str | None = Query(None),
    include_cancelled: bool = Query(False),
    db: Session = Depends(get_db),
) -> list[dict]:
    try:
        return svc.retrieve_appointments(
            db, phone=phone, email=email, include_cancelled=include_cancelled,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
