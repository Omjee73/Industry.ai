"""API tests: uploads, annotations, inspection, exports, dataset loader."""

from __future__ import annotations

import json
from typing import Dict, List

from fastapi.testclient import TestClient

from app.core import config


def _demo(name: str) -> bytes:
    return (config.DEMO_DIR / name).read_bytes()


def _upload(client: TestClient, url: str, data: bytes, name: str):
    return client.post(url, files={"file": (name, data, "image/png")})


def _upload_reference(client: TestClient) -> int:
    r = _upload(client, "/api/v1/reference", _demo("reference.png"), "reference.png")
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _annotate_with_manifest(client: TestClient, ref_id: int) -> None:
    manifest = json.loads((config.DEMO_DIR / "reference.json").read_text())
    r = client.post(
        f"/api/v1/reference/{ref_id}/annotations", json={"annotations": manifest["components"]}
    )
    assert r.status_code == 200, r.text


def _upload_tests(client: TestClient, names: List[str]) -> List[int]:
    ids = []
    for fname in names:
        r = _upload(client, "/api/v1/test", _demo(fname), fname)
        assert r.status_code == 200, r.text
        ids.append(r.json()["id"])
    return ids


def test_health(client: TestClient):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_upload_reference(client: TestClient):
    ref_id = _upload_reference(client)
    r = client.get(f"/api/v1/reference/{ref_id}/image")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("image/png")


def test_upload_rejects_invalid_images(client: TestClient):
    r = _upload(client, "/api/v1/reference", b"this is not an image", "bad.png")
    assert r.status_code == 400


def test_annotations_save_and_get(client: TestClient):
    ref_id = _upload_reference(client)
    payload = {
        "annotations": [
            {"name": "R1", "x": 0.0977, "y": 0.0781, "width": 0.0879, "height": 0.0339}
        ]
    }
    r = client.post(f"/api/v1/reference/{ref_id}/annotations", json=payload)
    assert r.status_code == 200, r.text
    saved = r.json()
    assert saved[0]["name"] == "R1"

    r = client.get(f"/api/v1/reference/{ref_id}/annotations")
    assert r.status_code == 200
    assert r.json()[0]["id"] == saved[0]["id"]

    # Replacing the set replaces everything.
    r = client.post(
        f"/api/v1/reference/{ref_id}/annotations",
        json={"annotations": [{"name": "RX", "x": 0.5, "y": 0.5, "width": 0.1, "height": 0.1}]},
    )
    assert r.status_code == 200
    names = [a["name"] for a in client.get(f"/api/v1/reference/{ref_id}/annotations").json()]
    assert names == ["RX"]


def test_annotation_validation(client: TestClient):
    ref_id = _upload_reference(client)
    bad = {"annotations": [{"name": "X", "x": 0.9, "y": 0.9, "width": 0.2, "height": 0.2}]}
    r = client.post(f"/api/v1/reference/{ref_id}/annotations", json=bad)
    assert r.status_code == 422  # out of bounds


def test_inspection_end_to_end(client: TestClient):
    ref_id = _upload_reference(client)
    _annotate_with_manifest(client, ref_id)
    test_ids = _upload_tests(
        client, ["test_01_complete.png", "test_02_missing_c1_d2.png", "test_03_missing_r2.png"]
    )

    r = client.post(
        "/api/v1/inspection", json={"reference_image_id": ref_id, "test_image_ids": test_ids}
    )
    assert r.status_code == 200, r.text
    payload: Dict = r.json()
    assert payload["status"] == "missing"
    by_id = {t["test_image_id"]: t for t in payload["test_images"]}

    complete = by_id[test_ids[0]]
    assert complete["status"] == "ok"
    assert all(c["status"] == "present" for c in complete["results"])

    missing = by_id[test_ids[1]]
    assert missing["status"] == "missing"
    assert {c["name"] for c in missing["results"] if c["status"] == "missing"} == {"C1", "D2"}

    r2 = by_id[test_ids[2]]
    assert r2["status"] == "missing"
    assert {c["name"] for c in r2["results"] if c["status"] == "missing"} == {"R2"}
    assert r2["image"]["url"].startswith("/api/v1/test/")


def test_inspection_validation(client: TestClient):
    ref_id = _upload_reference(client)
    r = client.post(
        "/api/v1/inspection", json={"reference_image_id": ref_id, "test_image_ids": []}
    )
    assert r.status_code == 422
    r = client.post("/api/v1/inspection", json={"reference_image_id": ref_id, "test_image_ids": [999]})
    assert r.status_code == 404


def test_export_json_and_csv(client: TestClient):
    ref_id = _upload_reference(client)
    _annotate_with_manifest(client, ref_id)
    test_ids = _upload_tests(client, ["test_01_complete.png", "test_02_missing_c1_d2.png"])
    r = client.post(
        "/api/v1/inspection", json={"reference_image_id": ref_id, "test_image_ids": test_ids}
    )
    assert r.status_code == 200
    inspection_id = r.json()["id"]

    r = client.get(f"/api/v1/inspection/{inspection_id}/export?format=json")
    assert r.status_code == 200
    assert r.json()["status"] == "missing"
    missing_names = {
        c["name"] for c in r.json()["test_images"][1]["results"] if c["status"] == "missing"
    }
    assert missing_names == {"C1", "D2"}

    r = client.get(f"/api/v1/inspection/{inspection_id}/export?format=csv")
    assert r.status_code == 200
    assert "C1" in r.text
    assert "inspection_id" in r.text

    r = client.get(f"/api/v1/inspection/{inspection_id}/export?format=xml")
    assert r.status_code == 400


def test_dataset_loader(client: TestClient):
    r = client.get("/api/v1/dataset/load")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["reference_id"] > 0
    assert {a["name"] for a in data["annotations"]} == {"R1", "R2", "C1", "C2", "U1", "U2", "D1", "D2"}
    assert len(data["test_ids"]) >= 1

    # Annotations are persisted on the reference image.
    anns = client.get(f"/api/v1/reference/{data['reference_id']}/annotations").json()
    assert len(anns) == 8
    assert anns[0]["name"] == "R1"
    # Test images are registered.
    for tid in data["test_ids"]:
        r = client.get(f"/api/v1/test/{tid}/image")
        assert r.status_code == 200
