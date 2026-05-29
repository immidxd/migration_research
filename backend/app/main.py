from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.app.settings import PROJECT_ROOT, get_settings
from backend.routers import flows as flows_router
from backend.routers import sources as sources_router
from backend.routers import stats as stats_router
from backend.routers import temporal as temporal_router
from backend.routers import territories as territories_router


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Migrations backend starting up")
    yield
    logger.info("Migrations backend shutting down")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Migrations Research API",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_dev_url, "http://127.0.0.1:8765"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    def health() -> JSONResponse:
        return JSONResponse({"status": "ok"})

    app.include_router(territories_router.router)
    app.include_router(temporal_router.router)
    app.include_router(sources_router.router)
    app.include_router(flows_router.router)
    app.include_router(stats_router.router)

    # Serve the built frontend if present.
    build_dir = PROJECT_ROOT / "frontend" / "build"
    if build_dir.exists():
        app.mount("/", StaticFiles(directory=str(build_dir), html=True), name="frontend")

    return app


app = create_app()
