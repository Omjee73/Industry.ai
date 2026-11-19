"""Export inspection results as JSON/CSV files (attachments)."""

from __future__ import annotations

import csv
import io
import json

from sqlalchemy.orm import Session

from ..database.models import Inspection


def _payload(db: Session, inspection: Inspection) -> dict:
    from .inspection_service import get_inspection_payload

    return get_inspection_payload(db, inspection)


def inspection_to_json(db: Session, inspection: Inspection) -> str:
    return json.dumps(_payload(db, inspection), indent=2)


def inspection_to_csv(db: Session, inspection: Inspection) -> str:
    payload = _payload(db, inspection)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "inspection_id",
            "test_image_id",
            "component_name",
            "status",
            "confidence",
            "explanation",
            "bbox_x",
            "bbox_y",
            "bbox_width",
            "bbox_height",
        ]
    )
    for t in payload["test_images"]:
        for r in t["results"]:
            b = r["bbox"]
            writer.writerow(
                [
                    inspection.id,
                    t["test_image_id"],
                    r["name"],
                    r["status"],
                    f"{r['confidence']:.3f}",
                    r["explanation"],
                    f"{b['x']:.4f}",
                    f"{b['y']:.4f}",
                    f"{b['width']:.4f}",
                    f"{b['height']:.4f}",
                ]
            )
    return buf.getvalue()
