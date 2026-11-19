"""API routes for the configurable inspection thresholds."""

from __future__ import annotations

from sqlalchemy.orm import Session

from ...database.db import get_db
from ...schemas.requests import SettingsUpdateIn
from ...schemas.responses import SettingsOut
from ...services import settings_service
from fastapi import APIRouter, Depends

router = APIRouter()


@router.get("/settings", response_model=SettingsOut)
def get_settings(db: Session = Depends(get_db)):
    return SettingsOut(
        thresholds=settings_service.get_thresholds(db),
        defaults=settings_service.get_defaults(),
    )


@router.put("/settings", response_model=SettingsOut)
def update_settings(payload: SettingsUpdateIn, db: Session = Depends(get_db)):
    thresholds = settings_service.set_thresholds(db, payload.thresholds)
    return SettingsOut(thresholds=thresholds, defaults=settings_service.get_defaults())
