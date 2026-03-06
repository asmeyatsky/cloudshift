"""FastAPI application factory for CloudShift.

Creates the app with CORS, lifespan, error handlers, and all route modules.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from cloudshift.presentation.api.routes import apply, config, patterns, plan, report, scan, validate
from cloudshift.presentation.api.schemas import ErrorResponse
from cloudshift.presentation.api.websocket import router as ws_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialize and tear down the DI container."""
    from cloudshift.infrastructure.config.dependency_injection import Container

    container = Container()
    app.state.container = container
    logger.info("DI container initialised")
    yield
    logger.info("Shutting down")


def create_app() -> FastAPI:
    """Build and return the configured FastAPI application."""
    app = FastAPI(
        title="CloudShift API",
        summary="Cloud migration automation platform",
        version="0.1.0",
        lifespan=_lifespan,
    )

    # -- CORS (allow all origins for local dev) ----------------------------
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # -- Route modules -----------------------------------------------------
    app.include_router(scan.router)
    app.include_router(plan.router)
    app.include_router(apply.router)
    app.include_router(validate.router)
    app.include_router(patterns.router)
    app.include_router(report.router)
    app.include_router(config.router)
    app.include_router(ws_router)

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

    return app
