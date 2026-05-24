"""SQLAlchemy engine / session — sync mode (simpler for this scope)."""
from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.core.config import settings

_engine = create_engine(
    f"sqlite:///{settings.SQLITE_DB_PATH}",
    connect_args={"check_same_thread": False},
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
Base = declarative_base()


def get_db() -> Iterator[Session]:
    """FastAPI dependency — yields a session, closes it at the end."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create tables if they don't exist."""
    # Importing models registers them with Base.metadata
    from app.db import models  # noqa: F401

    Base.metadata.create_all(bind=_engine)
