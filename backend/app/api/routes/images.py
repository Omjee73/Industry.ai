"""API routes for test images (the boards compared against the reference)."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ...database.db import get_db
from ...database.models import Image
from ...schemas.responses import ImageInfoOut, ImageUploadOut
from ...services import image_service

router = APIRouter()


@router.post("/test", response_model=ImageUploadOut)
async def upload_test(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Upload a test PCB image (same board/view as the reference)."""
    image = await image_service.save_uploaded_image(file, kind="test", role="test", db=db)
    return ImageUploadOut(
        id=image.id, width=image.width, height=image.height, url=f"/api/v1/test/{image.id}/image"
    )


@router.get("/test/{image_id}", response_model=ImageInfoOut)
def test_image_info(image_id: int, db: Session = Depends(get_db)):
    image = db.get(Image, image_id)
    if image is None or image.kind != "test":
        raise HTTPException(status_code=404, detail="Test image not found.")
    return ImageInfoOut(
        id=image.id,
        kind=image.kind,
        width=image.width,
        height=image.height,
        url=f"/api/v1/test/{image.id}/image",
        created_at=image.created_at.isoformat(),
    )


@router.get("/test/{image_id}/image")
def test_image(image_id: int, db: Session = Depends(get_db)):
    image = db.get(Image, image_id)
    if image is None or image.kind != "test":
        raise HTTPException(status_code=404, detail="Test image not found.")
    return FileResponse(image.file_path, media_type="image/png", filename=Path(image.file_path).name)
