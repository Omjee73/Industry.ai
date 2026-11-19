"""API routes for reference images + component annotations."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ...database.db import get_db
from ...database.models import Image
from ...schemas.requests import AnnotationsSaveIn
from ...schemas.responses import AnnotationOut, ImageInfoOut, ImageUploadOut
from ...services import annotation_service, image_service

router = APIRouter()


def _annotation_out(a) -> AnnotationOut:
    return AnnotationOut(id=a.id, name=a.name, x=a.x, y=a.y, width=a.width, height=a.height)


@router.post("/reference", response_model=ImageUploadOut)
async def upload_reference(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Upload the good/reference PCB image."""
    image = await image_service.save_uploaded_image(file, kind="reference", role="reference", db=db)
    return ImageUploadOut(
        id=image.id, width=image.width, height=image.height, url=f"/api/v1/reference/{image.id}/image"
    )


@router.get("/reference/latest", response_model=ImageInfoOut)
def latest_reference(db: Session = Depends(get_db)):
    image = db.query(Image).filter(Image.kind == "reference").order_by(Image.id.desc()).first()
    if image is None:
        raise HTTPException(status_code=404, detail="No reference image has been uploaded yet.")
    return ImageInfoOut(
        id=image.id,
        kind=image.kind,
        width=image.width,
        height=image.height,
        url=f"/api/v1/reference/{image.id}/image",
        created_at=image.created_at.isoformat(),
    )


@router.get("/reference/{image_id}/image")
def reference_image(image_id: int, db: Session = Depends(get_db)):
    image = db.get(Image, image_id)
    if image is None or image.kind != "reference":
        raise HTTPException(status_code=404, detail="Reference image not found.")
    return FileResponse(image.file_path, media_type="image/png", filename=Path(image.file_path).name)


@router.post("/reference/{image_id}/annotations", response_model=list[AnnotationOut])
def save_annotations(
    image_id: int, payload: AnnotationsSaveIn, db: Session = Depends(get_db)
):
    """Save the list of named, drawn component regions (normalized coordinates)."""
    annotations = annotation_service.save_annotations(db, image_id, payload.annotations)
    return [_annotation_out(a) for a in annotations]


@router.get("/reference/{image_id}/annotations", response_model=list[AnnotationOut])
def get_annotations(image_id: int, db: Session = Depends(get_db)):
    annotations = annotation_service.get_annotations(db, image_id)
    return [_annotation_out(a) for a in annotations]
