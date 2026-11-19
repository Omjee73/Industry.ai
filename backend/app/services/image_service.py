"""Image storage service: upload validation, file saving, DB registration."""

from __future__ import annotations

import hashlib
import uuid
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..core import config
from ..database.models import Image

MAX_UPLOAD_BYTES = 8 * 1024 * 1024  # 8 MB
MAX_PIXELS = 40_000_000


def safe_filename(name: Optional[str], default: str = "image") -> str:
    cleaned = "".join(c for c in Path(name or "").name if c.isalnum() or c in "-_.")
    cleaned = cleaned.strip("._-")[:64]
    return cleaned or default


def validate_upload(data: bytes, filename: str = "image.png") -> np.ndarray:
    """Decode an uploaded image; raises HTTPException for invalid uploads."""
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"Image '{safe_filename(filename)}' exceeds the 8 MB limit.",
        )
    arr = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if arr is None:
        raise HTTPException(
            status_code=400,
            detail=f"Could not decode image '{safe_filename(filename)}' "
                   f"(supported formats: PNG, JPEG, WEBP, BMP).",
        )
    h, w = arr.shape[:2]
    if w < 8 or h < 8 or w * h > MAX_PIXELS:
        raise HTTPException(
            status_code=400,
            detail=f"Image '{safe_filename(filename)}' has invalid dimensions {w}x{h}.",
        )
    return arr


def _register(arr: np.ndarray, kind: str, role: str, db: Session, path: Path, data: bytes) -> Image:
    h, w = arr.shape[:2]
    cv2.imwrite(str(path), arr)
    image = Image(
        kind=kind,
        role=role,
        file_path=str(path),
        width=int(w),
        height=int(h),
        sha256=hashlib.sha256(data).hexdigest(),
    )
    db.add(image)
    db.commit()
    db.refresh(image)
    return image


async def save_uploaded_image(file: UploadFile, kind: str, role: str, db: Session) -> Image:
    """Save an uploaded image to disk + DB and return the new record."""
    data = await file.read()
    arr = validate_upload(data, file.filename or "image")
    stem = safe_filename(file.filename, "image")
    fname = f"{kind}_{uuid.uuid4().hex[:12]}_{stem}.png"
    return _register(arr, kind, role, db, config.IMAGES_DIR / fname, data)


def register_file(path: Path, kind: str, role: str, db: Session) -> Image:
    """Register an existing image file on disk (used by the demo dataset loader)."""
    arr = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if arr is None:
        raise HTTPException(status_code=400, detail=f"Could not load image file {path}")
    target = config.IMAGES_DIR / f"{kind}_{uuid.uuid4().hex[:12]}_{path.stem}.png"
    return _register(arr, kind, role, db, target, path.read_bytes())


def load_gray(image: Image) -> Optional[np.ndarray]:
    return cv2.imread(image.file_path, cv2.IMREAD_GRAYSCALE)
