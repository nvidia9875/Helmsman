"""FastAPI application entrypoint.

Run locally:
    uv run uvicorn helmsman.api.main:app --reload --port 8000
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from helmsman.api.routers import bot, documents, health, meetings
from helmsman.core.config import get_settings
from helmsman.core.logging import (
    configure_logging,
    logger,
    setup_azure_monitor,
)


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[no-untyped-def]
    settings = get_settings()
    configure_logging(settings.log_level, json_output=settings.environment != "dev")
    monitor_on = setup_azure_monitor(settings.applicationinsights_connection_string)
    logger.info(
        "helmsman.starting",
        env=settings.environment,
        appinsights=monitor_on,
        auth_required=settings.helmsman_require_auth,
    )
    yield
    logger.info("helmsman.stopped")


_settings = get_settings()
# 本番: 信頼できる origin だけ。dev: localhost も追加。SWA hostname は env で上書き可能。
_default_origins = [
    "https://kind-glacier-0122f6400.7.azurestaticapps.net",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
if _settings.environment == "dev" and not _settings.cors_allowed_origins:
    _cors_origins = ["*"]
elif _settings.cors_allowed_origins:
    _cors_origins = _settings.cors_allowed_origins.split(",")
else:
    _cors_origins = _default_origins


app = FastAPI(
    title="Helmsman API",
    description="Goal-driven AI meeting facilitator backend",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(meetings.router)
app.include_router(documents.router)
app.include_router(bot.router)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """全 unhandled 例外を構造化ログ + 一律 500。stack trace は内部にだけ送る。"""
    logger.error(
        "api.unhandled_exception",
        method=request.method,
        path=request.url.path,
        error=str(exc),
        error_type=type(exc).__name__,
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "internal server error", "error_type": type(exc).__name__},
    )


@app.get("/")
async def root() -> dict[str, Any]:
    return {
        "service": "helmsman",
        "version": "0.1.0",
        "description": "Goal-driven AI meeting facilitator",
        "docs": "/docs",
    }
