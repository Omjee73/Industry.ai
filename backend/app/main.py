"""FastAPI application factory + entrypoint for the PCB Missing Component Detection backend."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .api.routes import dataset, health, images, inspection, reference, settings as settings_router
from .core import config
from .database.db import init_db


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title=config.APP_TITLE, version=config.APP_VERSION, lifespan=lifespan)
    app.include_router(health.router, prefix="/api/v1")
    app.include_router(reference.router, prefix="/api/v1")
    app.include_router(images.router, prefix="/api/v1")
    app.include_router(inspection.router, prefix="/api/v1")
    app.include_router(settings_router.router, prefix="/api/v1")
    app.include_router(dataset.router, prefix="/api/v1")

    if config.FRONTEND_DIST.exists():
        app.mount("/", StaticFiles(directory=str(config.FRONTEND_DIST), html=True), name="spa")
    return app


app = create_app()
