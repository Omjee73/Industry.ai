"""API route for the one-click synthetic demo dataset loader."""

from __future__ import annotations

from sqlalchemy.orm import Session

from ...database.db import get_db
from ...schemas.responses import DatasetLoadOut
from ...services import dataset_service
from fastapi import APIRouter, Depends

router = APIRouter()


@router.get("/dataset/load", response_model=DatasetLoadOut)
def load_demo_dataset(db: Session = Depends(get_db)):
    """Load the bundled reference + manifest annotations + demo test images."""
    return DatasetLoadOut(**dataset_service.load_demo_dataset(db))
