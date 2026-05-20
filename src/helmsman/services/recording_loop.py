"""Microsoft Graph Calling recordResponse API で Teams 会議音声を chunk 録音する。

Service-hosted bot は raw 音声を取れないため、`recordResponse` で短時間 WAV を取得し、
Azure Speech で文字化して既存 tick pipeline に流す。

制約:
- 1 chunk あたり最大 ~10 秒 (Microsoft Graph 仕様)
- chunk 境界で音声欠落あり
- Rate limit: 9 records/min/call 程度
- recordResponse はもともと IVR 用 ("press 1") なので prompts: [] で silent loop にする

フロー:
1. bot が会議に established → `start_recording(call_id, meeting_id, organizer_id)`
2. recording loop が定期的に `POST /communications/calls/{id}/recordResponse`
3. Microsoft → webhook で `recordingOperationCompleted` を送ってくる
4. webhook handler が recording URL を download → STT → tick に流す
"""
from __future__ import annotations

import asyncio
from typing import Any

import httpx

from helmsman.core.logging import logger
from helmsman.services.graph_calling import GRAPH_API_BASE, get_graph_token

# 進行中の recording loop タスク: call_id → asyncio.Task
_recording_tasks: dict[str, asyncio.Task[None]] = {}

# call_id → (meeting_id, organizer_id) の追加マップ
# (graph_calling._call_registry にも同じ情報があるが、こちらは録音専用に別途持つ)
_recording_meta: dict[str, tuple[str, str]] = {}

# 1 chunk の長さ (秒)
CHUNK_DURATION_SEC = 10
# chunk 間の sleep (秒、rate limit 回避)
INTER_CHUNK_SLEEP_SEC = 1


async def _trigger_recording(call_id: str) -> dict[str, Any] | None:
    """1 chunk 分の録音を Graph API で開始する (非同期、結果は webhook で返る)。

    Returns:
        Graph API のレスポンス (operation 情報) or None (エラー時)
    """
    try:
        token = await get_graph_token()
    except Exception as e:  # noqa: BLE001
        logger.warning("recording.token_failed", call_id=call_id, error=str(e))
        return None

    payload: dict[str, Any] = {
        "bargeInAllowed": True,
        "prompts": [],
        "maxRecordDurationInSeconds": CHUNK_DURATION_SEC,
        "initialSilenceTimeoutInSeconds": CHUNK_DURATION_SEC,
        "maxSilenceTimeoutInSeconds": CHUNK_DURATION_SEC,
        "playBeep": False,
        "stopTones": [],
        "clientContext": f"chunk:{call_id}",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.post(
                f"{GRAPH_API_BASE}/communications/calls/{call_id}/recordResponse",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
        except httpx.HTTPError as e:
            logger.warning("recording.request_failed", call_id=call_id, error=str(e))
            return None

        if resp.status_code >= 400:
            logger.warning(
                "recording.bad_status",
                call_id=call_id,
                status=resp.status_code,
                body=resp.text[:300],
            )
            return None

        try:
            data = resp.json()
        except ValueError:
            data = {}
        logger.info("recording.chunk_triggered", call_id=call_id, op=data.get("id"))
        return data


async def _recording_loop(call_id: str, meeting_id: str, organizer_id: str) -> None:
    """call 中ずっと回り続ける録音ループ。task が cancel されるまで continue。"""
    logger.info(
        "recording.loop_started", call_id=call_id, meeting_id=meeting_id
    )
    try:
        while True:
            result = await _trigger_recording(call_id)
            # 録音は ~CHUNK_DURATION_SEC かかる + webhook 経由で別途処理
            # ここでは次の chunk まで待つだけ
            sleep_for = CHUNK_DURATION_SEC + INTER_CHUNK_SLEEP_SEC
            if result is None:
                # 失敗時は少し長めに待ってリトライ
                sleep_for = max(sleep_for, 5)
            await asyncio.sleep(sleep_for)
    except asyncio.CancelledError:
        logger.info("recording.loop_cancelled", call_id=call_id)
        raise
    except Exception as e:  # noqa: BLE001
        logger.error(
            "recording.loop_crashed", call_id=call_id, error=str(e), error_type=type(e).__name__
        )
        raise


def start_recording(call_id: str, meeting_id: str, organizer_id: str) -> None:
    """call の音声録音ループを開始する。既に走ってる call には何もしない (idempotent)。"""
    existing = _recording_tasks.get(call_id)
    if existing and not existing.done():
        return
    _recording_meta[call_id] = (meeting_id, organizer_id)
    task = asyncio.create_task(_recording_loop(call_id, meeting_id, organizer_id))
    _recording_tasks[call_id] = task
    logger.info(
        "recording.start", call_id=call_id, meeting_id=meeting_id, organizer_id=organizer_id
    )


def stop_recording(call_id: str) -> None:
    """call の録音ループを停止する。"""
    task = _recording_tasks.pop(call_id, None)
    _recording_meta.pop(call_id, None)
    if task and not task.done():
        task.cancel()
        logger.info("recording.stop", call_id=call_id)


def is_recording(call_id: str) -> bool:
    """call が録音中かどうか。"""
    task = _recording_tasks.get(call_id)
    return task is not None and not task.done()


def get_recording_meta(call_id: str) -> tuple[str | None, str | None]:
    """call_id から (meeting_id, organizer_id) を返す。録音中でないなら (None, None)。"""
    meta = _recording_meta.get(call_id)
    if meta:
        return meta
    return None, None
