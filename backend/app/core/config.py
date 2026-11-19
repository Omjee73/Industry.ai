"""Runtime configuration, derived from the environment."""

from __future__ import annotations

import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]  # .../backend/app/core/config.py -> backend/
REPO_ROOT = BACKEND_DIR.parent

DATA_DIR = Path(os.environ.get("PCB_DATA_DIR", str(BACKEND_DIR / "data")))
IMAGES_DIR = DATA_DIR / "images"
DEMO_DIR = DATA_DIR / "demo"
DB_PATH = DATA_DIR / "app.db"

FRONTEND_DIST = REPO_ROOT / "frontend" / "dist"

APP_TITLE = "PCB Missing Component Detection"
APP_VERSION = "1.0.0"

API_PREFIX = "/api/v1"

MAX_TEST_IMAGES_PER_INSPECTION = 3
