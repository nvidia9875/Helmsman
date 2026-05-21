"""Microsoft Graph Communications playPrompt で会議内に TTS 音声を流す。

ACS 時代の bidirectional WebSocket TTS の代替 (M.D)。フロー:
1. text を Azure Speech TTS で raw PCM (16kHz/16bit/mono) に
2. WAV ヘッダを付けて in-memory cache に登録 (uuid キー)
3. /static/tts/{key}.wav エンドポイントが Microsoft Graph に WAV を提供
4. POST /communications/calls/{id}/playPrompt で再生をリクエスト
5. Microsoft が WAV を fetch → 会議で再生
"""
from __future__ import annotations

import struct
import uuid
from typing import Any

import httpx

from helmsman.core.config import get_settings
from helmsman.core.logging import logger
from helmsman.services.graph_calling import GRAPH_API_BASE, get_graph_token
from helmsman.services.recording_loop import (
    pause_recording_for_tts,
    resume_recording_after_tts,
)
from helmsman.services.tts import synthesize_pcm

# tts key → WAV bytes (process-local)
_tts_cache: dict[str, bytes] = {}


# 末尾の silence padding (Microsoft が音声末尾を早めに完了報告する傾向への対策)
TRAILING_SILENCE_MS = 1500


def _pcm_to_wav(pcm: bytes, sample_rate: int = 16000) -> bytes:
    """raw PCM (16-bit mono) を WAV ヘッダ付き bytes に。末尾に silence padding 追加。"""
    # 末尾に TRAILING_SILENCE_MS の silence を足す (Microsoft が末尾を切るのを防ぐ)
    silence_bytes = sample_rate * 2 * TRAILING_SILENCE_MS // 1000
    pcm_padded = pcm + (b"\x00" * silence_bytes)
    data_size = len(pcm_padded)
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
    return header + pcm_padded


def get_cached_tts(key: str) -> bytes | None:
    """key で WAV bytes を取得 (削除しない、Microsoft が再 fetch することがあるため)。"""
    return _tts_cache.get(key)


def drop_cached_tts(key: str) -> None:
    _tts_cache.pop(key, None)


async def play_text_in_graph_call(call_id: str, text: str) -> bool:
    """call で text を TTS 発話させる。

    Returns:
        True: Graph に playPrompt 受理された (会議で再生される)
        False: TTS 合成失敗 / Graph エラー / 設定不備

    Note:
        Microsoft Graph は call あたり 1 media operation のみ同時実行可能。
        recordResponse loop が走ってると playPrompt を打ち切るため、TTS 中は
        loop を pause する (pause_recording_for_tts / resume_recording_after_tts)。
        再生完了は webhook の playPromptOperation completed イベントで検知して
        resume するが、念のため synthesize_pcm の長さから推定した duration 後に
        background task で resume も予約する。
    """
    text = (text or "").strip()
    if not text:
        return False

    settings = get_settings()
    base = (settings.acs_callback_base_url or "").rstrip("/")
    if not base:
        logger.warning("graph_tts.no_base_url")
        return False

    try:
        pcm = await synthesize_pcm(text)
    except Exception as e:  # noqa: BLE001
        logger.warning("graph_tts.synth_failed", error=str(e))
        return False

    wav = _pcm_to_wav(pcm)
    key = uuid.uuid4().hex
    _tts_cache[key] = wav
    wav_url = f"{base}/static/tts/{key}.wav"

    try:
        token = await get_graph_token()
    except Exception as e:  # noqa: BLE001
        logger.warning("graph_tts.token_failed", error=str(e))
        drop_cached_tts(key)
        return False

    payload: dict[str, Any] = {
        "prompts": [
            {
                "@odata.type": "#microsoft.graph.mediaPrompt",
                "mediaInfo": {
                    "@odata.type": "#microsoft.graph.mediaInfo",
                    "uri": wav_url,
                    "resourceId": uuid.uuid4().hex,
                },
            }
        ],
        "clientContext": f"tts:{key}",
    }

    # 再生中は recording loop を pause (1 op only 制限への対処)
    pause_recording_for_tts(call_id)

    # 推定再生時間 = PCM の長さ + Microsoft 側の playback queue 遅延 + 安全マージン
    # 内訳: PCM bytes / (16000 Hz * 2 bytes/sample) + queue 遅延 3s + safety 2s
    pcm_duration_sec = len(pcm) / 32000.0
    estimated_duration_sec = pcm_duration_sec + 5.0

    async def _auto_resume() -> None:
        import asyncio as _asyncio
        await _asyncio.sleep(estimated_duration_sec)
        resume_recording_after_tts(call_id)
        logger.info(
            "graph_tts.auto_resume_fallback",
            call_id=call_id,
            after_sec=round(estimated_duration_sec, 1),
        )

    import asyncio as _asyncio
    _asyncio.create_task(_auto_resume())

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.post(
                f"{GRAPH_API_BASE}/communications/calls/{call_id}/playPrompt",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
        except httpx.HTTPError as e:
            logger.warning("graph_tts.request_failed", error=str(e))
            drop_cached_tts(key)
            resume_recording_after_tts(call_id)
            return False

        if resp.status_code >= 400:
            logger.warning(
                "graph_tts.bad_status",
                status=resp.status_code,
                body=resp.text[:300],
                text=text[:80],
            )
            drop_cached_tts(key)
            resume_recording_after_tts(call_id)
            return False

        try:
            op = resp.json()
        except ValueError:
            op = {}
        logger.info(
            "graph_tts.queued",
            call_id=call_id,
            op_id=op.get("id"),
            wav_bytes=len(wav),
            duration_sec=round(estimated_duration_sec - 2.0, 1),
            text=text[:80],
        )
        # cache cleanup は webhook の playPromptOperation completed 受信時に
        return True
