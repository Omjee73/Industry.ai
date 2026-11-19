"""Smoke test: upload reference + annotate + upload tests + inspect + export (TestClient)."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app.core import config
from app.main import app


def main() -> int:
    demo = config.DEMO_DIR
    reference_file = demo / "reference.png"
    if not reference_file.exists():
        print(f"MISSING demo data: {reference_file}. Run: python backend/scripts/generate_dataset.py")
        return 2
    test_files = sorted(demo.glob("test_*.png"))[:3]

    with TestClient(app) as client:
        r = client.post("/api/v1/reference", files={"file": ("reference.png", reference_file.read_bytes(), "image/png")})
        assert r.status_code == 200, r.text
        ref_id = r.json()["id"]
        print(f"[ok] reference uploaded: id={ref_id} {r.json()['width']}x{r.json()['height']}")

        manifest = json.loads((demo / "reference.json").read_text())
        r = client.post(f"/api/v1/reference/{ref_id}/annotations", json={"annotations": manifest["components"]})
        assert r.status_code == 200, r.text
        print(f"[ok] annotations saved: {[a['name'] for a in r.json()]}")

        test_ids = []
        for f in test_files:
            r = client.post("/api/v1/test", files={"file": (f.name, f.read_bytes(), "image/png")})
            assert r.status_code == 200, r.text
            test_ids.append(r.json()["id"])
            print(f"[ok] test uploaded: {f.name} id={r.json()['id']}")

        r = client.post("/api/v1/inspection", json={"reference_image_id": ref_id, "test_image_ids": test_ids})
        assert r.status_code == 200, r.text
        payload = r.json()
        print(f"[ok] inspection {payload['id']} status={payload['status']}")
        for t in payload["test_images"]:
            print(f"     test {t['test_image_id']}: {t['status']}")
            for c in t["results"]:
                print(f"       {c['name']:>3} {c['status']:>7} conf={c['confidence']:.3f} {c['explanation']}")

        for fmt in ("json", "csv"):
            r = client.get(f"/api/v1/inspection/{payload['id']}/export?format={fmt}")
            assert r.status_code == 200, r.text
            print(f"[ok] export {fmt}: {len(r.content)} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
