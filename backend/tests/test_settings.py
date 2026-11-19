"""Settings API tests: GET defaults, PUT updates, validation, persistence."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_get_settings(client: TestClient):
    r = client.get("/api/v1/settings")
    assert r.status_code == 200
    data = r.json()
    assert set(data["thresholds"]) == set(data["defaults"])
    for key in data["defaults"]:
        assert data["thresholds"][key] == data["defaults"][key]


def test_update_settings_persists(client: TestClient):
    r = client.get("/api/v1/settings")
    assert r.status_code == 200
    before = r.json()["thresholds"]["diff_ok"]
    try:
        r = client.put("/api/v1/settings", json={"thresholds": {"diff_ok": 0.11}})
        assert r.status_code == 200
        assert r.json()["thresholds"]["diff_ok"] == 0.11
        r = client.get("/api/v1/settings")
        assert r.json()["thresholds"]["diff_ok"] == 0.11
    finally:
        client.put("/api/v1/settings", json={"thresholds": {"diff_ok": before}})


def test_update_settings_rejects_bad_key(client: TestClient):
    r = client.put("/api/v1/settings", json={"thresholds": {"nope": 0.5}})
    assert r.status_code == 400


def test_update_settings_rejects_out_of_range(client: TestClient):
    r = client.put("/api/v1/settings", json={"thresholds": {"diff_ok": 1.7}})
    assert r.status_code == 400
