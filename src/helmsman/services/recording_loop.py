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
import uuid
from datetime import UTC, datetime
from typing import Any

import httpx

from helmsman.core.config import get_settings
from helmsman.core.logging import logger
from helmsman.services.graph_calling import GRAPH_API_BASE, get_graph_token


def _silent_prompt_url() -> str:
    """Microsoft Graph recordResponse の prompts に渡す silent WAV の URL。

    api/main.py の /static/silent.wav (500ms 無音) を参照。
    """
    s = get_settings()
    base = (s.acs_callback_base_url or "").rstrip("/")
    return f"{base}/static/silent.wav"

# 進行中の recording loop タスク: call_id → asyncio.Task
_recording_tasks: dict[str, asyncio.Task[None]] = {}

# call_id → (meeting_id, organizer_id) の追加マップ
# (graph_calling._call_registry にも同じ情報があるが、こちらは録音専用に別途持つ)
_recording_meta: dict[str, tuple[str, str]] = {}

# TTS playPrompt 中の call_id 集合。recording loop はこの間 chunk trigger をスキップする。
# Microsoft Graph は call あたり 1 media operation しか同時実行できないため、
# recordResponse loop が playPrompt を割り込んで打ち切ってしまう問題への対処。
_tts_paused_calls: set[str] = set()


def pause_recording_for_tts(call_id: str) -> None:
    """TTS 再生中は recording loop を一時停止する。play_text_in_graph_call から呼ぶ。"""
    _tts_paused_calls.add(call_id)


def resume_recording_after_tts(call_id: str) -> None:
    _tts_paused_calls.discard(call_id)


def is_paused_for_tts(call_id: str) -> bool:
    return call_id in _tts_paused_calls


# 1 chunk の長さ (秒)。Microsoft Graph 仕様で max 60s だが、長すぎると遅延悪化。
CHUNK_DURATION_SEC = 10
# chunk 間の sleep (秒)。0 にして実質ゼロ gap、Microsoft 側 rate limit に当たれば調整。
INTER_CHUNK_SLEEP_SEC = 0
# recordResponse が「call が存在しない」系エラー (404 / 400) を連続でこの回数返したら、
# Graph の disconnect webhook が来ていなくても会議終了とみなして自動でクリーンアップする。
# 10s chunk × 3 = ~30s の猶予 — 一時的な API hiccup での誤検知を避けつつ素早く回復。
CALL_GONE_FAILURE_THRESHOLD = 3
# 「call が消えた」とみなす HTTP ステータス。
_CALL_GONE_STATUSES = frozenset({400, 404})


async def _trigger_recording(call_id: str) -> tuple[dict[str, Any] | None, int]:
    """1 chunk 分の録音を Graph API で開始する (非同期、結果は webhook で返る)。

    Returns:
        (data, status):
        - 成功時は (Graph API レスポンス, HTTP ステータス)
        - エラー時は (None, HTTP ステータス)。ネットワークエラー/トークン失敗は status=0。
    """
    try:
        token = await get_graph_token()
    except Exception as e:  # noqa: BLE001
        logger.warning("recording.token_failed", call_id=call_id, error=str(e))
        return None, 0

    # Microsoft 仕様: prompts は 1 件必須 (空 [] や 2 件以上は error code 8523)。
    # silent WAV を 1 件だけ渡す。
    payload: dict[str, Any] = {
        "bargeInAllowed": True,
        "prompts": [
            {
                "@odata.type": "#microsoft.graph.mediaPrompt",
                "mediaInfo": {
                    "@odata.type": "#microsoft.graph.mediaInfo",
                    "uri": _silent_prompt_url(),
                    "resourceId": str(uuid.uuid4()),
                },
            }
        ],
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
            return None, 0

        if resp.status_code >= 400:
            logger.warning(
                "recording.bad_status",
                call_id=call_id,
                status=resp.status_code,
                body=resp.text[:300],
            )
            return None, resp.status_code

        try:
            data = resp.json()
        except ValueError:
            data = {}
        logger.info("recording.chunk_triggered", call_id=call_id, op=data.get("id"))
        return data, resp.status_code


async def _recording_loop(call_id: str, meeting_id: str, organizer_id: str) -> None:
    """call 中ずっと回り続ける録音ループ。task が cancel されるまで continue。

    Graph の disconnect webhook が届かず会議が終わっても bot_status が in_call の
    まま固まる現象への防御として、recordResponse が「call なし」系エラー (404/400)
    を連続で返したら会議終了とみなして自動クリーンアップする。
    """
    logger.info(
        "recording.loop_started", call_id=call_id, meeting_id=meeting_id
    )
    consecutive_gone = 0
    try:
        while True:
            # TTS 再生中なら chunk trigger をスキップ
            if is_paused_for_tts(call_id):
                logger.info("recording.paused_for_tts", call_id=call_id)
                await asyncio.sleep(1)
                continue
            result, http_status = await _trigger_recording(call_id)
            # 録音は ~CHUNK_DURATION_SEC かかる + webhook 経由で別途処理
            # ここでは次の chunk まで待つだけ
            sleep_for = CHUNK_DURATION_SEC + INTER_CHUNK_SLEEP_SEC
            if result is None:
                # 失敗時は少し長めに待ってリトライ
                sleep_for = max(sleep_for, 5)

            # call が消えた系エラーを連続でカウント。閾値に達したら会議終了とみなす。
            if http_status in _CALL_GONE_STATUSES:
                consecutive_gone += 1
                logger.info(
                    "recording.call_gone_suspected",
                    call_id=call_id,
                    status=http_status,
                    consecutive=consecutive_gone,
                )
                if consecutive_gone >= CALL_GONE_FAILURE_THRESHOLD:
                    await _self_heal_call_ended(call_id, meeting_id, organizer_id)
                    return
            else:
                # 成功 or 一時的エラーならカウンタをリセット
                consecutive_gone = 0

            await asyncio.sleep(sleep_for)
    except asyncio.CancelledError:
        logger.info("recording.loop_cancelled", call_id=call_id)
        raise
    except Exception as e:  # noqa: BLE001
        logger.error(
            "recording.loop_crashed", call_id=call_id, error=str(e), error_type=type(e).__name__
        )
        raise


async def _self_heal_call_ended(
    call_id: str, meeting_id: str, organizer_id: str
) -> None:
    """recordResponse が call なしを連続で返した = 会議終了。webhook 不達でも自力で回復する。

    bot.py の disconnect ハンドラと同じクリーンアップ (call registry / 録音 /
    CallSession 削除) に加え、meeting の bot_status を disconnected、state を
    concluded に書き戻す。ダッシュボードを誰も開いていなくても発火する点が
    meetings.py の lazy stale-sweep との違い。
    """
    logger.warning(
        "recording.self_heal_call_ended",
        call_id=call_id,
        meeting_id=meeting_id,
    )
    # 遅延 import で循環参照を回避 (bot.py の disconnect ハンドラと対称)。
    from helmsman.models.meeting import MeetingState
    from helmsman.repositories.meetings import MeetingRepository
    from helmsman.services.call_buffer import get_call_registry
    from helmsman.services.graph_calling import unregister_call

    # 録音ループ自身は return で止まるが、registry/session 側も掃除する。
    unregister_call(call_id)
    try:
        await get_call_registry().drop(call_id)
    except Exception as e:  # noqa: BLE001
        logger.warning(
            "recording.self_heal_session_drop_failed", call_id=call_id, error=str(e)
        )

    try:
        repo = MeetingRepository()
        meeting = await repo.get(meeting_id, organizer_id)
        if meeting is not None:
            meeting.bot_status = "disconnected"
            meeting.bot_call_connection_id = None
            meeting.bot_last_event_at = datetime.now(UTC)
            if meeting.state != MeetingState.CONCLUDED:
                meeting.state = MeetingState.CONCLUDED
                if meeting.ended_at is None:
                    meeting.ended_at = datetime.now(UTC)
            await repo.upsert(meeting)
    except Exception as e:  # noqa: BLE001
        logger.warning(
            "recording.self_heal_meeting_update_failed",
            call_id=call_id,
            meeting_id=meeting_id,
            error=str(e),
        )

    # _recording_tasks / _recording_meta から自分を外す (stop_recording 相当だが
    # task.cancel は呼ばない — 既に return 直前で自分が止まるため)。
    _recording_tasks.pop(call_id, None)
    _recording_meta.pop(call_id, None)


def start_recording(call_id: str, meeting_id: str, organizer_id: str) -> None:
    """call の音声録音ループを開始する。既に走ってる call には何もしない (idempotent)。

    CallSession も同時に作成しておく ( /bot/transcript polling が即座に
    bot_active=true を返せるよう。utterance はまだ空)。
    """
    existing = _recording_tasks.get(call_id)
    if existing and not existing.done():
        return
    _recording_meta[call_id] = (meeting_id, organizer_id)

    # CallSession を先に作る (background task で)
    async def _bootstrap() -> None:
        from helmsman.services.call_buffer import get_call_registry
        registry = get_call_registry()
        await registry.get_or_create(
            call_connection_id=call_id,
            meeting_id=meeting_id,
            organizer_id=organizer_id,
        )

    asyncio.create_task(_bootstrap())

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
