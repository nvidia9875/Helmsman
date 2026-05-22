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

from helmsman.api.routers import bot, decisions, documents, groups, health, meetings
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
app.include_router(groups.router)
app.include_router(bot.router)
app.include_router(decisions.router)


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


# 500ms silent WAV (16kHz, 16-bit, mono) を在中バッファとして 1 回だけ生成
def _build_silent_wav(duration_ms: int = 500) -> bytes:
    import struct
    sample_rate = 16000
    num_samples = sample_rate * duration_ms // 1000
    data_size = num_samples * 2  # 16-bit = 2 bytes
    header = (
        b"RIFF"
        + struct.pack("<I", 36 + data_size)
        + b"WAVEfmt "
        + struct.pack("<I", 16)
        + struct.pack("<H", 1)
        + struct.pack("<H", 1)
        + struct.pack("<I", sample_rate)
        + struct.pack("<I", sample_rate * 2)
        + struct.pack("<H", 2)
        + struct.pack("<H", 16)
        + b"data"
        + struct.pack("<I", data_size)
    )
    return header + (b"\x00" * data_size)


_SILENT_WAV_BYTES = _build_silent_wav(duration_ms=100)


@app.get("/static/silent.wav")
async def silent_wav() -> Any:
    """Microsoft Graph recordResponse prompts 用の silent WAV (16kHz/16bit/mono, 100ms)。

    Service-hosted bot で audio capture するために prompts 配列に 1 件以上必須。
    silent prompt で実質無音から録音開始する。
    """
    from fastapi import Response

    return Response(content=_SILENT_WAV_BYTES, media_type="audio/wav")


@app.get("/static/tts/{key}.wav")
async def tts_wav(key: str) -> Any:
    """Microsoft Graph playPrompt 用の動的 TTS WAV。

    `services/graph_play_prompt.py` が in-memory cache に WAV を登録する。
    Microsoft が GET でフェッチ → 会議で再生。
    """
    from fastapi import HTTPException, Response

    from helmsman.services.graph_play_prompt import get_cached_tts

    wav = get_cached_tts(key)
    if wav is None:
        raise HTTPException(status_code=404, detail="tts not found")
    return Response(content=wav, media_type="audio/wav")
