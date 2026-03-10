"""FastAPI application factory for CloudShift.

Creates the app with CORS, lifespan, error handlers, and all route modules.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from cloudshift.infrastructure.config.settings import Settings
from cloudshift.presentation.api.dependencies import verify_auth
from cloudshift.presentation.api.routes import apply, auth as auth_router, config, patterns, plan, report, projects, scan, validate
from cloudshift.presentation.api.schemas import ErrorResponse
from cloudshift.presentation.api.websocket import router as ws_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialize and tear down the DI container."""
    from cloudshift.infrastructure.config.dependency_injection import Container

    # Use settings from app state if available, else default
    settings = getattr(app.state, "settings", None)
    container = Container(settings=settings)
    app.state.container = container
    logger.info("DI container initialised")
    yield
    logger.info("Shutting down")


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build and return the configured FastAPI application."""
    settings = settings or Settings()
    app = FastAPI(
        title="CloudShift API",
        summary="Cloud migration automation platform",
        version="0.1.0",
        lifespan=_lifespan,
    )
    app.state.settings = settings

    # -- CORS (restrict to configured origins) ----------------------------
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # -- Auth (public: login, mode) -----------------------------------------
    app.include_router(auth_router.router)

    # -- Route modules (Protected) -----------------------------------------
    protected_deps = [Depends(verify_auth)]
    app.include_router(scan.router, dependencies=protected_deps)
    app.include_router(plan.router, dependencies=protected_deps)
    app.include_router(apply.router, dependencies=protected_deps)
    app.include_router(validate.router, dependencies=protected_deps)
    app.include_router(patterns.router, dependencies=protected_deps)
    app.include_router(report.router, dependencies=protected_deps)
    app.include_router(config.router, dependencies=protected_deps)
    app.include_router(projects.router, dependencies=protected_deps)
    app.include_router(ws_router, dependencies=protected_deps)

    # -- Error handlers ----------------------------------------------------

    @app.exception_handler(ValueError)
    async def value_error_handler(_request: Request, exc: ValueError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=ErrorResponse(detail=str(exc)).model_dump(),
        )

    @app.exception_handler(Exception)
    async def generic_error_handler(_request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error: %s", exc)
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(detail="Internal server error").model_dump(),
        )

    # -- Health check ------------------------------------------------------

    @app.get("/health", tags=["meta"], summary="Health check")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    # -- Root, assets, and favicon (serve Web UI) --------------------------
    static_path = settings.static_dir.resolve()
    index_html = static_path / "index.html"
    if index_html.exists():

        @app.get("/", include_in_schema=False)
        async def root() -> FileResponse:
            return FileResponse(index_html, media_type="text/html")

    assets_dir = static_path / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon() -> Response:
        return Response(status_code=204)

    return app
