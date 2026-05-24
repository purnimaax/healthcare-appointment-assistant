"""Appointment business logic.

Keeping this in a service layer (separate from tools and routes) means the
same validation runs whether the request comes from the AI agent or the REST API.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.db.models import Appointment, User

log = get_logger(__name__)

# Mock hospital data — in production this would come from an EMR/HIS
DEPARTMENTS: dict[str, list[str]] = {
    "General Medicine": ["Dr. Anjali Rao", "Dr. Imran Sheikh"],
    "Cardiology": ["Dr. Vivek Menon", "Dr. Sneha Iyer"],
    "Orthopedics": ["Dr. Rahul Verma"],
    "Dermatology": ["Dr. Priya Nair"],
    "Pediatrics": ["Dr. Kavita Joshi"],
    "ENT": ["Dr. Arjun Pillai"],
}

# 30-minute slots, 09:00 to 16:30
DAILY_SLOTS: list[str] = [
    f"{h:02d}:{m:02d}" for h in range(9, 17) for m in (0, 30)
]


def _resolve_doctor(department: str, doctor: Optional[str]) -> tuple[str, str]:
    """Match department and doctor names (case-insensitive). Returns (dept, doctor)."""
    dept_match = next(
        (d for d in DEPARTMENTS if d.lower() == department.lower()), None
    )
    if not dept_match:
        raise ValueError(
            f"Unknown department '{department}'. Available: {', '.join(DEPARTMENTS)}"
        )

    doctors = DEPARTMENTS[dept_match]
    if doctor:
        doc_match = next((d for d in doctors if d.lower() == doctor.lower()), None)
        if not doc_match:
            raise ValueError(
                f"'{doctor}' not found in {dept_match}. Options: {', '.join(doctors)}"
            )
        return dept_match, doc_match
    return dept_match, doctors[0]


def _parse_date(d: str) -> date:
    try:
        parsed = datetime.strptime(d, "%Y-%m-%d").date()
    except ValueError as e:
        raise ValueError(f"Invalid date '{d}'. Use YYYY-MM-DD.") from e
    if parsed < date.today():
        raise ValueError("Can't book appointments in the past.")
    return parsed


def _validate_slot(slot: str) -> None:
    if slot not in DAILY_SLOTS:
        raise ValueError(
            f"'{slot}' isn't a valid slot. Clinic runs 09:00–16:30 in 30-min steps."
        )


def get_or_create_user(
    db: Session,
    name: str,
    phone: Optional[str] = None,
    email: Optional[str] = None,
) -> User:
    """Look up a patient by phone or email; create a new record if not found."""
    if not phone and not email:
        raise ValueError("Need either phone or email to identify the patient.")

    if phone:
        user = db.query(User).filter(User.phone == phone).first()
        if user:
            return user
    if email:
        user = db.query(User).filter(User.email == email).first()
        if user:
            return user

    user = User(name=name, phone=phone, email=email)
    db.add(user)
    db.commit()
    db.refresh(user)
    log.info("Created user id=%s name=%s", user.id, user.name)
    return user


def fetch_available_slots(
    db: Session,
    department: str,
    appointment_date: str,
    doctor: Optional[str] = None,
) -> dict:
    """Return open slots for a doctor on a given date."""
    dept, doc = _resolve_doctor(department, doctor)
    _parse_date(appointment_date)

    taken = {
        a.time_slot
        for a in db.query(Appointment).filter(
            Appointment.doctor == doc,
            Appointment.appointment_date == appointment_date,
            Appointment.status == "booked",
        )
    }
    available = [s for s in DAILY_SLOTS if s not in taken]
    return {
        "department": dept,
        "doctor": doc,
        "date": appointment_date,
        "available_slots": available,
        "total_available": len(available),
    }


def book_appointment(
    db: Session,
    *,
    name: str,
    phone: Optional[str],
    email: Optional[str],
    department: str,
    appointment_date: str,
    time_slot: str,
    doctor: Optional[str] = None,
    notes: Optional[str] = None,
) -> dict:
    dept, doc = _resolve_doctor(department, doctor)
    _parse_date(appointment_date)
    _validate_slot(time_slot)

    user = get_or_create_user(db, name=name, phone=phone, email=email)

    appt = Appointment(
        user_id=user.id,
        department=dept,
        doctor=doc,
        appointment_date=appointment_date,
        time_slot=time_slot,
        status="booked",
        notes=notes,
    )
    db.add(appt)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError(
            f"{doc} is already booked at {appointment_date} {time_slot}."
        )
    db.refresh(appt)
    log.info("Booked appointment id=%s for user=%s", appt.id, user.id)

    return {
        "appointment_id": appt.id,
        "patient": user.name,
        "department": appt.department,
        "doctor": appt.doctor,
        "date": appt.appointment_date,
        "time": appt.time_slot,
        "status": appt.status,
    }


def cancel_appointment(db: Session, appointment_id: int) -> dict:
    appt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appt:
        raise ValueError(f"No appointment with id={appointment_id}.")
    if appt.status == "cancelled":
        return {"appointment_id": appt.id, "status": "already_cancelled"}

    appt.status = "cancelled"
    db.commit()
    log.info("Cancelled appointment id=%s", appt.id)
    return {"appointment_id": appt.id, "status": "cancelled"}


def modify_appointment(
    db: Session,
    appointment_id: int,
    *,
    new_date: Optional[str] = None,
    new_time_slot: Optional[str] = None,
) -> dict:
    appt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appt:
        raise ValueError(f"No appointment with id={appointment_id}.")
    if appt.status != "booked":
        raise ValueError(f"Can't modify a {appt.status} appointment.")
    if not new_date and not new_time_slot:
        raise ValueError("Provide new_date and/or new_time_slot.")

    target_date = new_date or appt.appointment_date
    target_slot = new_time_slot or appt.time_slot
    _parse_date(target_date)
    _validate_slot(target_slot)

    clash = (
        db.query(Appointment)
        .filter(
            Appointment.doctor == appt.doctor,
            Appointment.appointment_date == target_date,
            Appointment.time_slot == target_slot,
            Appointment.status == "booked",
            Appointment.id != appt.id,
        )
        .first()
    )
    if clash:
        raise ValueError(
            f"{appt.doctor} is already booked at {target_date} {target_slot}."
        )

    appt.appointment_date = target_date
    appt.time_slot = target_slot
    db.commit()
    db.refresh(appt)
    log.info("Modified appointment id=%s", appt.id)
    return {
        "appointment_id": appt.id,
        "doctor": appt.doctor,
        "date": appt.appointment_date,
        "time": appt.time_slot,
        "status": appt.status,
    }


def retrieve_appointments(
    db: Session,
    *,
    phone: Optional[str] = None,
    email: Optional[str] = None,
    include_cancelled: bool = False,
) -> list[dict]:
    if not phone and not email:
        raise ValueError("Need phone or email to look up appointments.")

    user = (
        db.query(User).filter(User.phone == phone).first()
        if phone
        else db.query(User).filter(User.email == email).first()
    )
    if not user:
        return []

    q = db.query(Appointment).filter(Appointment.user_id == user.id)
    if not include_cancelled:
        q = q.filter(Appointment.status != "cancelled")

    appts = q.order_by(
        Appointment.appointment_date.desc(), Appointment.time_slot.desc()
    ).all()

    return [
        {
            "appointment_id": a.id,
            "department": a.department,
            "doctor": a.doctor,
            "date": a.appointment_date,
            "time": a.time_slot,
            "status": a.status,
            "notes": a.notes,
        }
        for a in appts
    ]


def list_departments_and_doctors() -> dict[str, list[str]]:
    return DEPARTMENTS


def default_search_date_range() -> tuple[str, str]:
    today = date.today()
    return today.isoformat(), (today + timedelta(days=14)).isoformat()
