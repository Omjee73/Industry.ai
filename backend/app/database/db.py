"""SQLite database setup (SQLAlchemy)."""

from __future__ import annotations

from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from ..core import config


def _ensure_dirs() -> None:
    config.IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    config.DEMO_DIR.mkdir(parents=True, exist_ok=True)
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)


def init_db() -> None:
    """Create directories and all tables."""
    _ensure_dirs()
    from ..database import models  # noqa: F401  (import for side effects)

    models.Base.metadata.create_all(bind=engine)


_ensure_dirs()
engine = create_engine(f"sqlite:///{config.DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
