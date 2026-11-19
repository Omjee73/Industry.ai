"""Configurable inspection thresholds (SQLite-backed settings table)."""

from __future__ import annotations

from typing import Dict

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..cv.detector import DEFAULT_THRESHOLDS
from ..database.models import Setting


def get_thresholds(db: Session) -> Dict[str, float]:
    rows = {r.key: r.value for r in db.query(Setting).all()}
    return {
        **{k: float(v) for k, v in DEFAULT_THRESHOLDS.items()},
        **{k: float(v) for k, v in rows.items() if k in DEFAULT_THRESHOLDS},
    }


def get_defaults() -> Dict[str, float]:
    return {k: float(v) for k, v in DEFAULT_THRESHOLDS.items()}


def set_thresholds(db: Session, updates: Dict[str, float]) -> Dict[str, float]:
    """Persist user-provided threshold overrides; validates keys and ranges."""
    for key, value in updates.items():
        if key not in DEFAULT_THRESHOLDS:
            raise HTTPException(status_code=400, detail=f"Unknown setting: {key!r}")
        if not (0.0 <= value <= 1.0):
            raise HTTPException(
                status_code=400, detail=f"Setting {key!r} must be within [0, 1], got {value}."
            )
        row = db.get(Setting, key)
        if row is None:
            db.add(Setting(key=key, value=str(value)))
        else:
            row.value = str(value)
    db.commit()
    return get_thresholds(db)
