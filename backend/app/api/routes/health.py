"""API route for health checks."""

from __future__ import annotations

from fastapi import APIRouter

from ...core import config

router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "version": config.APP_VERSION}
