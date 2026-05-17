"""Health check endpoints."""
from __future__ import annotations

from fastapi import APIRouter

from helmsman.core.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/config")
async def config_check() -> dict[str, str]:
    """設定が読めているかを確認するエンドポイント (機密値は伏せる)。"""
    s = get_settings()
    return {
        "env": s.environment,
        "openai_endpoint": s.azure_openai_endpoint,
        "openai_deployment_high": s.azure_openai_deployment_high,
        "openai_deployment_mini": s.azure_openai_deployment_mini,
        "openai_deployment_realtime": s.azure_openai_deployment_realtime,
        "speech_region": s.azure_speech_region or "not-set",
        "cosmos_endpoint": s.cosmos_endpoint,
        "cosmos_database": s.cosmos_database,
        "signalr_configured": "yes" if s.signalr_connection_string else "no",
    }
