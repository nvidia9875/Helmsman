"""FastAPI application entrypoint.

Run locally:
    uv run uvicorn helmsman.api.main:app --reload --port 8000
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from helmsman.api.routers import documents, health, meetings
from helmsman.core.config import get_settings
from helmsman.core.logging import configure_logging, logger


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[no-untyped-def]
    settings = get_settings()
    configure_logging(settings.log_level)
    logger.info("helmsman.starting", env=settings.environment)
    yield
    logger.info("helmsman.stopped")


app = FastAPI(
    title="Helmsman API",
    description="Goal-driven AI meeting facilitator backend",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # dev only - 本番では絞る
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(meetings.router)
app.include_router(documents.router)


@app.get("/")
async def root() -> dict[str, Any]:
    return {
        "service": "helmsman",
        "version": "0.1.0",
        "description": "Goal-driven AI meeting facilitator",
        "docs": "/docs",
    }
