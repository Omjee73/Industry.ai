"""API routes for starting inspections + downloading results."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from ...database.db import get_db
from ...database.models import Image, Inspection
from ...schemas.requests import InspectionIn
from ...schemas.responses import InspectionOut
from ...services import export_service, inspection_service

router = APIRouter()


def _validate(db: Session, payload: InspectionIn):
    reference = db.get(Image, payload.reference_image_id)
    if reference is None or reference.kind != "reference":
        raise HTTPException(
            status_code=404, detail=f"Reference image {payload.reference_image_id} not found."
        )
    test_images = []
    for tid in payload.test_image_ids:
        img = db.get(Image, tid)
        if img is None or img.kind != "test":
            raise HTTPException(status_code=404, detail=f"Test image {tid} not found.")
        test_images.append(img)
    return reference, test_images


@router.post("/inspection", response_model=InspectionOut)
def start_inspection(payload: InspectionIn, db: Session = Depends(get_db)):
    """Run the CV pipeline on the reference + up to 3 test images."""
    reference, test_images = _validate(db, payload)
    inspection = inspection_service.run_inspection(db, reference, test_images)
    return InspectionOut(**inspection_service.get_inspection_payload(db, inspection))


@router.get("/inspection/{inspection_id}", response_model=InspectionOut)
def get_inspection(inspection_id: int, db: Session = Depends(get_db)):
    inspection = db.get(Inspection, inspection_id)
    if inspection is None:
        raise HTTPException(status_code=404, detail=f"Inspection {inspection_id} not found.")
    return InspectionOut(**inspection_service.get_inspection_payload(db, inspection))


@router.get("/inspection/{inspection_id}/export")
def export_inspection(inspection_id: int, format: str = "json", db: Session = Depends(get_db)):
    """Download the inspection results as JSON or CSV."""
    inspection = db.get(Inspection, inspection_id)
    if inspection is None:
        raise HTTPException(status_code=404, detail="Inspection not found.")
    if format == "json":
        return Response(
            content=export_service.inspection_to_json(db, inspection),
            media_type="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="inspection_{inspection.id}_results.json"'
            },
        )
    if format == "csv":
        return Response(
            content=export_service.inspection_to_csv(db, inspection),
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="inspection_{inspection.id}_results.csv"'
            },
        )
    raise HTTPException(status_code=400, detail="format must be 'json' or 'csv'.")
