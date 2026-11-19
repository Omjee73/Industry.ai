"""One-click loader for the bundled synthetic demo dataset."""

from __future__ import annotations

import json
from typing import Any, Dict, List

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..core import config
from ..database.models import Annotation, Image
from . import image_service


def load_demo_dataset(db: Session) -> Dict[str, Any]:
    """Load the reference board + manifest annotations + demo test images."""
    reference = (
        db.query(Image).filter(Image.kind == "reference").order_by(Image.id.desc()).first()
    )
    manifest_path = config.DEMO_DIR / "reference.json"
    if reference is None or not manifest_path.exists():
        raise HTTPException(
            status_code=400,
            detail="Demo dataset not found. Generate it first (see README: python "
                   "backend/scripts/generate_dataset.py).",
        )

    manifest = json.loads(manifest_path.read_text())
    db.query(Annotation).filter(Annotation.reference_image_id == reference.id).delete()
    db.commit()

    annotations: List[Annotation] = []
    for i, comp in enumerate(manifest["components"]):
        ann = Annotation(
            reference_image_id=reference.id,
            name=comp["name"],
            x=float(comp["x"]),
            y=float(comp["y"]),
            width=float(comp["width"]),
            height=float(comp["height"]),
            order=i,
        )
        db.add(ann)
        annotations.append(ann)
    db.commit()

    test_ids: List[int] = []
    for path in sorted(config.DEMO_DIR.glob("test_*.png")):
        image = image_service.register_file(path, kind="test", role="test", db=db)
        test_ids.append(image.id)
    if not test_ids:
        raise HTTPException(
            status_code=400, detail="No demo test images found in the demo dataset directory."
        )

    return {
        "reference_id": reference.id,
        "reference_url": f"/api/v1/reference/{reference.id}/image",
        "annotations": [
            {"id": a.id, "name": a.name, "x": a.x, "y": a.y, "width": a.width, "height": a.height}
            for a in annotations
        ],
        "test_ids": test_ids,
        "message": f"Loaded demo dataset: reference + {len(test_ids)} test images.",
    }
