"""Pytest fixtures: isolated data dir, TestClient, DB session."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

# Make the backend package importable regardless of how pytest was invoked.
BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

# Isolated data dir for tests (images, app.db, generated demo data).
_TMP = Path(tempfile.mkdtemp(prefix="pcb-backend-test-"))
os.environ["PCB_DATA_DIR"] = str(_TMP)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core import config  # noqa: E402
from app.database.db import SessionLocal, init_db  # noqa: E402
from app.main import app  # noqa: E402

# Generate the bundled demo dataset into the isolated data dir if it is missing.
if not (config.DEMO_DIR / "reference.png").exists():
    from scripts.generate_dataset import generate_dataset  # noqa: E402

    generate_dataset(config.DEMO_DIR)

init_db()


@pytest.fixture()
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def db() -> SessionLocal:
    d = SessionLocal()
    try:
        yield d
    finally:
        d.close()
