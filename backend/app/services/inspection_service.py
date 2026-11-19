"""Run inspections: align each test image, detect missing components, persist results."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Tuple

import cv2
from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..cv import detector, pipeline
from ..database.models import Annotation, Image, Inspection, TestImage
from . import settings_service


def _specs_from_annotations(db: Session, reference_id: int) -> List[detector.ComponentSpec]:
    annotations: List[Annotation] = (
        db.query(Annotation)
        .filter(Annotation.reference_image_id == reference_id)
        .order_by(Annotation.order, Annotation.id)
        .all()
    )
    return [
        detector.ComponentSpec(name=a.name, x=a.x, y=a.y, width=a.width, height=a.height)
        for a in annotations
    ]


def run_inspection(db: Session, reference: Image, test_images: List[Image]) -> Inspection:
    """Run the CV pipeline on each test image and store the inspection results."""
    specs = _specs_from_annotations(db, reference.id)
    ref_gray = cv2.imread(reference.file_path, cv2.IMREAD_GRAYSCALE)
    if ref_gray is None:
        raise HTTPException(status_code=500, detail="Failed to load the reference image.")
    thresholds = settings_service.get_thresholds(db)

    inspection = Inspection(reference_image_id=reference.id, status="running", results_json="{}")
    db.add(inspection)
    db.commit()
    db.refresh(inspection)

    results_by_test: Dict[str, Dict[str, Any]] = {}
    overall = "ok"
    for img in test_images:
        test_gray = cv2.imread(img.file_path, cv2.IMREAD_GRAYSCALE)
        if test_gray is None:
            raise HTTPException(status_code=500, detail=f"Failed to load test image {img.id}.")
        report = pipeline.inspect_board(ref_gray, test_gray, specs, thresholds)
        db.add(TestImage(image_id=img.id, inspection_id=inspection.id))
        db.commit()

        items = [
            {
                "name": r.name,
                "status": r.status,
                "confidence": r.confidence,
                "explanation": r.explanation,
                "bbox": r.bbox,
            }
            for r in report.results
        ]
        statuses = [i["status"] for i in items]
        if "missing" in statuses:
            image_status, overall = "missing", "missing"
        elif "review" in statuses:
            image_status = "review"
            if overall != "missing":
                overall = "review"
        else:
            image_status = "ok"
        results_by_test[str(img.id)] = {"status": image_status, "results": items}

    inspection.status = overall or "ok"
    inspection.results_json = json.dumps({"results": results_by_test})
    db.commit()
    db.refresh(inspection)
    return inspection


def get_inspection_payload(db: Session, inspection: Inspection) -> Dict[str, Any]:
    """Build the API payload for an inspection (mirrors InspectionOut)."""
    data = json.loads(inspection.results_json).get("results", {})
    test_rows: List[TestImage] = (
        db.query(TestImage).filter(TestImage.inspection_id == inspection.id).all()
    )
    images = {t.image_id: db.get(Image, t.image_id) for t in test_rows}

    test_out = []
    for tid in sorted(data.keys(), key=lambda x: int(x)):
        entry = data[tid]
        img = images.get(int(tid))
        test_out.append(
            {
                "test_image_id": int(tid),
                "status": entry["status"],
                "results": entry["results"],
                "image": {
                    "id": img.id,
                    "url": f"/api/v1/test/{img.id}/image",
                    "width": img.width,
                    "height": img.height,
                }
                if img
                else None,
            }
        )
    return {
        "id": inspection.id,
        "status": inspection.status,
        "reference_image_id": inspection.reference_image_id,
        "test_images": test_out,
    }
