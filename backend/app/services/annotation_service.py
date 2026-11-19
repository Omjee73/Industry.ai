"""Component annotation persistence (reference board annotations)."""

from __future__ import annotations

from typing import List

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..database.models import Annotation, Image
from ..schemas.requests import AnnotationIn


def save_annotations(db: Session, reference_id: int, items: List[AnnotationIn]) -> List[Annotation]:
    """Replace the annotation set of a reference image (atomic delete+insert)."""
    image = db.get(Image, reference_id)
    if image is None:
        raise HTTPException(status_code=404, detail=f"Reference image {reference_id} not found.")
    if image.kind != "reference":
        raise HTTPException(status_code=400, detail="Annotations are only allowed on reference images.")

    cleaned = []
    for i, item in enumerate(items):
        name = item.name.strip() or f"Unnamed {i + 1}"
        x = min(max(item.x, 0.0), 0.999)
        y = min(max(item.y, 0.0), 0.999)
        width = min(max(item.width, 0.001), max(0.0, 1.0 - x))
        height = min(max(item.height, 0.001), max(0.0, 1.0 - y))
        cleaned.append((name, x, y, width, height))

    db.query(Annotation).filter(Annotation.reference_image_id == reference_id).delete()
    db.commit()

    annotations: List[Annotation] = []
    for i, (name, x, y, width, height) in enumerate(cleaned):
        ann = Annotation(
            reference_image_id=reference_id, name=name, x=x, y=y, width=width, height=height, order=i
        )
        db.add(ann)
        annotations.append(ann)
    db.commit()
    return annotations


def get_annotations(db: Session, reference_id: int) -> List[Annotation]:
    image = db.get(Image, reference_id)
    if image is None:
        raise HTTPException(status_code=404, detail=f"Reference image {reference_id} not found.")
    return (
        db.query(Annotation)
        .filter(Annotation.reference_image_id == reference_id)
        .order_by(Annotation.order, Annotation.id)
        .all()
    )
