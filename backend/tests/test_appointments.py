"""Tests for appointment service logic.

No LLM needed here — just checking that validation, slot availability,
and the booking lifecycle behave correctly. Run with: cd backend && pytest -q
"""
from __future__ import annotations

import os
from datetime import date, timedelta

os.environ["SQLITE_DB_PATH"] = ":memory:"
os.environ["CHECKPOINT_DB_PATH"] = ":memory:"

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.services import appointments as svc


@pytest.fixture
def db():
    """Fresh in-memory DB per test."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    s = Session()
    try:
        yield s
    finally:
        s.close()


@pytest.fixture
def future_date() -> str:
    return (date.today() + timedelta(days=3)).isoformat()


def test_list_departments_returns_known_set():
    depts = svc.list_departments_and_doctors()
    assert "Cardiology" in depts
    assert "Dr. Vivek Menon" in depts["Cardiology"]


def test_fetch_slots_full_day_when_empty(db, future_date):
    result = svc.fetch_available_slots(db, department="Cardiology", appointment_date=future_date)
    assert result["doctor"] == "Dr. Vivek Menon"
    assert "09:00" in result["available_slots"]
    assert result["total_available"] == 16


def test_fetch_slots_rejects_unknown_department(db, future_date):
    with pytest.raises(ValueError, match="Unknown department"):
        svc.fetch_available_slots(db, department="Telepathy", appointment_date=future_date)


def test_fetch_slots_rejects_past_date(db):
    past = (date.today() - timedelta(days=1)).isoformat()
    with pytest.raises(ValueError, match="past"):
        svc.fetch_available_slots(db, department="Cardiology", appointment_date=past)


def test_book_appointment_happy_path(db, future_date):
    result = svc.book_appointment(
        db,
        name="Test Patient", phone="9999999999", email=None,
        department="Cardiology", appointment_date=future_date, time_slot="10:00",
    )
    assert result["status"] == "booked"
    assert result["appointment_id"] > 0
    assert result["doctor"] == "Dr. Vivek Menon"


def test_book_rejects_double_booking(db, future_date):
    svc.book_appointment(
        db, name="A", phone="111", email=None,
        department="Cardiology", appointment_date=future_date, time_slot="10:00",
    )
    with pytest.raises(ValueError, match="already booked"):
        svc.book_appointment(
            db, name="B", phone="222", email=None,
            department="Cardiology", appointment_date=future_date, time_slot="10:00",
        )


def test_book_rejects_invalid_slot(db, future_date):
    with pytest.raises(ValueError, match="valid slot"):
        svc.book_appointment(
            db, name="X", phone="123", email=None,
            department="Cardiology", appointment_date=future_date, time_slot="10:15",
        )


def test_fetch_slots_excludes_booked(db, future_date):
    svc.book_appointment(
        db, name="A", phone="111", email=None,
        department="Cardiology", appointment_date=future_date, time_slot="10:00",
    )
    result = svc.fetch_available_slots(db, department="Cardiology", appointment_date=future_date)
    assert "10:00" not in result["available_slots"]
    assert result["total_available"] == 15


def test_cancel_appointment(db, future_date):
    booked = svc.book_appointment(
        db, name="A", phone="111", email=None,
        department="Cardiology", appointment_date=future_date, time_slot="11:00",
    )
    result = svc.cancel_appointment(db, booked["appointment_id"])
    assert result["status"] == "cancelled"


def test_modify_appointment(db, future_date):
    booked = svc.book_appointment(
        db, name="A", phone="111", email=None,
        department="Cardiology", appointment_date=future_date, time_slot="11:00",
    )
    result = svc.modify_appointment(db, booked["appointment_id"], new_time_slot="14:00")
    assert result["time"] == "14:00"


def test_modify_rejects_clash(db, future_date):
    a = svc.book_appointment(
        db, name="A", phone="111", email=None,
        department="Cardiology", appointment_date=future_date, time_slot="11:00",
    )
    svc.book_appointment(
        db, name="B", phone="222", email=None,
        department="Cardiology", appointment_date=future_date, time_slot="12:00",
    )
    with pytest.raises(ValueError, match="already booked"):
        svc.modify_appointment(db, a["appointment_id"], new_time_slot="12:00")


def test_retrieve_appointments_by_phone(db, future_date):
    svc.book_appointment(
        db, name="A", phone="9988776655", email=None,
        department="Dermatology", appointment_date=future_date, time_slot="09:30",
    )
    svc.book_appointment(
        db, name="A", phone="9988776655", email=None,
        department="ENT", appointment_date=future_date, time_slot="14:00",
    )
    appts = svc.retrieve_appointments(db, phone="9988776655")
    assert len(appts) == 2


def test_get_or_create_user_deduplicates(db):
    u1 = svc.get_or_create_user(db, name="A", phone="555")
    u2 = svc.get_or_create_user(db, name="A again", phone="555")
    assert u1.id == u2.id
