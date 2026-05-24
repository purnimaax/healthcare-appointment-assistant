"""ORM models for the appointment system."""
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.session import Base


class User(Base):
    """A patient. Identified by phone (preferred) or email."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False)
    phone = Column(String(20), unique=True, index=True, nullable=True)
    email = Column(String(120), unique=True, index=True, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    appointments = relationship(
        "Appointment", back_populates="user", cascade="all, delete-orphan"
    )


class Appointment(Base):
    """A booked slot. Status: booked | cancelled | completed."""

    __tablename__ = "appointments"
    __table_args__ = (
        UniqueConstraint(
            "doctor", "appointment_date", "time_slot", name="uq_doctor_slot"
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    department = Column(String(80), nullable=False)
    doctor = Column(String(120), nullable=False)
    appointment_date = Column(String(10), nullable=False)  # YYYY-MM-DD
    time_slot = Column(String(5), nullable=False)  # HH:MM (24h)
    status = Column(String(20), default="booked", nullable=False)
    notes = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="appointments")
