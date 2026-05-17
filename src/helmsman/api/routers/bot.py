"""Helmsman Bot endpoints — Teams 会議への招待 + ACS Call Automation webhook 受け口。

Flow:
  1. UI が POST /meetings/{id}/bot/invite {teams_meeting_url}
  2. Helmsman → ACS Call Automation: connect_call(teams meeting locator)
  3. ACS → 会議に Helmsman (External) として参加
  4. ACS → POST {callback_base}/bot/callback (CallConnected / CallDisconnected 等)
  5. それを Meeting.bot_status に反映 + Cosmos に永続化
"""
from __future__ import annotations

import asyncio
import base64
import json
from datetime import UTC, datetime
from typing import Any

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from pydantic import BaseModel, Field

from helmsman.api.security import require_api_key
from helmsman.core.logging import logger
from helmsman.models.meeting import Meeting
from helmsman.repositories.meetings import MeetingRepository
from helmsman.services.call_buffer import (
    UNKNOWN_PARTICIPANT_ID,
    get_call_registry,
    get_or_create_transcriber,
    start_session_ticker,
    start_transcriber_consumer,
)
from helmsman.services.teams_bot import (
    hangup_bot,
    invite_bot_to_teams_meeting,
    parse_operation_context,
)

router = APIRouter(tags=["bot"])


def get_repo() -> MeetingRepository:
    return MeetingRepository()


# ---------- request / response schemas ----------

class InviteBotRequest(BaseModel):
    teams_meeting_url: str = Field(..., min_length=10, max_length=2000)


class InviteBotResponse(BaseModel):
    meeting: Meeting
    call_connection_id: str


# ---------- bot lifecycle ----------

@router.post(
    "/meetings/{meeting_id}/bot/invite",
    response_model=InviteBotResponse,
    dependencies=[Depends(require_api_key)],
)
async def invite_bot(
    meeting_id: str,
    organizer_id: str,
    req: InviteBotRequest,
    repo: MeetingRepository = Depends(get_repo),
) -> InviteBotResponse:
    """Helmsman bot を Teams 会議に参加させる。"""
    meeting = await repo.get(meeting_id, organizer_id)
    if not meeting:
        raise HTTPException(404, "meeting not found")

    try:
        connection_id = await invite_bot_to_teams_meeting(
            meeting_id=meeting_id,
            organizer_id=organizer_id,
            teams_meeting_url=req.teams_meeting_url,
        )
    except RuntimeError as e:
        # 設定不備
        raise HTTPException(503, str(e)) from e
    except Exception as e:  # noqa: BLE001
        logger.error("bot.invite_failed", meeting_id=meeting_id, error=str(e))
        meeting.bot_status = "failed"
        meeting.bot_last_event_at = datetime.now(UTC)
        await repo.upsert(meeting)
        raise HTTPException(502, f"ACS join failed: {e}") from e

    meeting.teams_meeting_url = req.teams_meeting_url
    meeting.bot_call_connection_id = connection_id
    meeting.bot_status = "connecting"
    meeting.bot_last_event_at = datetime.now(UTC)
    await repo.upsert(meeting)

    return InviteBotResponse(meeting=meeting, call_connection_id=connection_id)


class BotTranscriptResponse(BaseModel):
    bot_active: bool
    utterance_count: int
    utterances: list[dict[str, Any]]


class SpeakRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=600)


class SpeakResponse(BaseModel):
    accepted: bool
    detail: str


@router.post(
    "/meetings/{meeting_id}/bot/speak",
    response_model=SpeakResponse,
    dependencies=[Depends(require_api_key)],
)
async def speak_into_meeting(
    meeting_id: str,
    organizer_id: str,
    req: SpeakRequest,
    repo: MeetingRepository = Depends(get_repo),
) -> SpeakResponse:
    """Helmsman bot に任意のテキストを会議で発話させる (DOC-9 「読み上げ」ボタン用)。

    Bot が active なセッションを持っていないと 409。
    """
    meeting = await repo.get(meeting_id, organizer_id)
    if not meeting:
        raise HTTPException(404, "meeting not found")

    registry = get_call_registry()
    session = await registry.lookup_by_meeting(meeting_id)
    if not session or session.media_ws is None:
        raise HTTPException(
            409,
            "bot is not in a call right now — invite the bot to a Teams meeting first",
        )

    from helmsman.services.tts import speak_into_call

    asyncio.create_task(speak_into_call(session.media_ws, req.text))
    logger.info(
        "bot.manual_speak",
        meeting_id=meeting_id,
        text=req.text[:80],
    )
    return SpeakResponse(accepted=True, detail="TTS playback queued")


@router.get(
    "/meetings/{meeting_id}/bot/transcript",
    response_model=BotTranscriptResponse,
    dependencies=[Depends(require_api_key)],
)
async def get_bot_transcript(
    meeting_id: str,
    organizer_id: str,
    limit: int = 50,
) -> BotTranscriptResponse:
    """Bot がリアルタイムで拾った発言の一覧 (in-memory バッファ)。

    Bot が active な間だけ意味ある値が返る。会議終了後は空。
    """
    registry = get_call_registry()
    session = await registry.lookup_by_meeting(meeting_id)
    if not session:
        return BotTranscriptResponse(bot_active=False, utterance_count=0, utterances=[])
    tail = session.utterances[-limit:]
    return BotTranscriptResponse(
        bot_active=True,
        utterance_count=len(session.utterances),
        utterances=[u.model_dump(mode="json") for u in tail],
    )


@router.post(
    "/meetings/{meeting_id}/bot/leave",
    response_model=Meeting,
    dependencies=[Depends(require_api_key)],
)
async def leave_bot(
    meeting_id: str,
    organizer_id: str,
    repo: MeetingRepository = Depends(get_repo),
) -> Meeting:
    """Helmsman bot を会議から退出させる。"""
    meeting = await repo.get(meeting_id, organizer_id)
    if not meeting:
        raise HTTPException(404, "meeting not found")
    if meeting.bot_call_connection_id:
        await hangup_bot(meeting.bot_call_connection_id)
    meeting.bot_status = "disconnected"
    meeting.bot_call_connection_id = None
    meeting.bot_last_event_at = datetime.now(UTC)
    await repo.upsert(meeting)
    return meeting


# ---------- ACS Call Automation webhook (no auth — ACS callback) ----------

# ACS webhook events 一覧:
# https://learn.microsoft.com/azure/communication-services/concepts/call-automation/events
_STATUS_BY_EVENT = {
    "Microsoft.Communication.CallConnected": "in_call",
    "Microsoft.Communication.CallDisconnected": "disconnected",
    "Microsoft.Communication.CallTransferAccepted": "in_call",
    "Microsoft.Communication.CallTransferFailed": "failed",
    "Microsoft.Communication.ParticipantsUpdated": None,  # status 変えない
}


# ---------- ACS Media Streaming WebSocket (audio in) ----------

@router.websocket("/bot/media-stream/{meeting_id}/{organizer_id}")
async def acs_media_stream(
    websocket: WebSocket,
    meeting_id: str,
    organizer_id: str,
) -> None:
    """ACS から会議音声 (raw PCM 16kHz/16bit/mono) を受け取る WebSocket。

    ACS は JSON フレームを送ってくる:
      - {"kind":"AudioMetadata","audioMetadata":{...}}  (最初の1フレーム)
      - {"kind":"AudioData","audioData":{"data":"<base64>","silent":false,...}}

    audio チャンクを Speech SDK に流し込み、認識結果を別 task で消費する。
    """
    await websocket.accept()
    logger.info(
        "ws.connected", meeting_id=meeting_id, organizer_id=organizer_id
    )

    registry = get_call_registry()
    # call_connection_id は AudioMetadata の correlationId にも入るが、
    # meeting_id ベースで 1 セッション 1 通話とする (MVP)
    session = await registry.get_or_create(
        call_connection_id=f"ws:{meeting_id}",
        meeting_id=meeting_id,
        organizer_id=organizer_id,
    )
    # TTS が会議に音声を送るための参照を保存
    session.media_ws = websocket

    # 定期 tick は session に 1 つあれば足りる (発言が来なくても TimeKeeper 用)
    if session.ticker_task is None or session.ticker_task.done():
        session.ticker_task = asyncio.create_task(start_session_ticker(session))

    try:
        while True:
            msg = await websocket.receive_text()
            try:
                payload = json.loads(msg)
            except json.JSONDecodeError:
                continue
            kind = payload.get("kind")
            if kind == "AudioMetadata":
                meta = payload.get("audioMetadata", {})
                logger.info(
                    "ws.audio_metadata",
                    meeting_id=meeting_id,
                    sample_rate=meta.get("sampleRate"),
                    channels=meta.get("channels"),
                    encoding=meta.get("encoding"),
                )
            elif kind == "AudioData":
                data = payload.get("audioData", {})
                if data.get("silent"):
                    continue
                b64 = data.get("data", "")
                if not b64:
                    continue
                try:
                    pcm = base64.b64decode(b64)
                except (ValueError, TypeError) as e:
                    logger.warning("ws.audio_decode_failed", error=str(e))
                    continue

                # UNMIXED: participantRawID が AudioData に同梱される。
                # 形式は SDK バージョン差があるので複数キーを試す。
                participant_id = (
                    data.get("participantRawID")
                    or data.get("participantRawId")
                    or data.get("participantId")
                    or (data.get("participant") or {}).get("rawId")
                    or (data.get("participant") or {}).get("raw_id")
                    or UNKNOWN_PARTICIPANT_ID
                )

                try:
                    transcriber, is_new = get_or_create_transcriber(
                        session, participant_id=participant_id
                    )
                except RuntimeError:
                    await websocket.close(code=1011)
                    return

                if is_new:
                    # この participant の認識結果を消費する task を起こす
                    session.consumer_tasks[participant_id] = asyncio.create_task(
                        start_transcriber_consumer(session, transcriber)
                    )

                transcriber.push_audio(pcm)
    except WebSocketDisconnect:
        logger.info("ws.disconnected", meeting_id=meeting_id)
    except Exception as e:  # noqa: BLE001
        logger.error("ws.error", error=str(e))
    finally:
        session.media_ws = None
        await registry.drop(session.call_connection_id)


# ---------- ACS Call Automation webhook (no auth — ACS callback) ----------


@router.post("/bot/callback", status_code=status.HTTP_200_OK)
async def acs_callback(
    request: Request,
    repo: MeetingRepository = Depends(get_repo),
) -> dict[str, Any]:
    """ACS Call Automation からの cloud event webhook。

    ACS はイベントを配列で送ってくる。各イベントの data.callConnectionId と
    operationContext で meeting を引いて状態更新する。
    """
    events = await request.json()
    if not isinstance(events, list):
        events = [events]

    handled = 0
    for ev in events:
        event_type = ev.get("type") or ev.get("eventType") or ""
        data = ev.get("data", {})

        # Event Grid validation handshake (subscription 時のみ)
        if event_type == "Microsoft.EventGrid.SubscriptionValidationEvent":
            return {"validationResponse": data.get("validationCode", "")}

        operation_context = data.get("operationContext", "")
        call_connection_id = data.get("callConnectionId", "")
        meeting_id, organizer_id = parse_operation_context(operation_context)
        logger.info(
            "bot.event",
            event_type=event_type,
            call_connection_id=call_connection_id,
            meeting_id=meeting_id,
            organizer_id=organizer_id,
        )

        if not (meeting_id and organizer_id):
            continue

        meeting = await repo.get(meeting_id, organizer_id)
        if not meeting:
            logger.warning(
                "bot.event_unknown_meeting",
                meeting_id=meeting_id,
                organizer_id=organizer_id,
            )
            continue

        new_status = _STATUS_BY_EVENT.get(event_type)
        meeting.bot_last_event_at = datetime.now(UTC)
        if new_status is not None:
            meeting.bot_status = new_status
            if new_status == "disconnected":
                meeting.bot_call_connection_id = None
        await repo.upsert(meeting)

        # UNMIXED: ParticipantsUpdated で participantRawID → displayName を session に学習
        if event_type == "Microsoft.Communication.ParticipantsUpdated":
            _refresh_participants_cache(meeting_id, data)
        handled += 1

    return {"handled": handled}


def _refresh_participants_cache(meeting_id: str, event_data: dict[str, Any]) -> None:
    """ParticipantsUpdated payload から rawId → displayName を抽出して session に保存。

    ACS payload は SDK バージョン差で構造が揺れるので、複数キーを試す。
    """
    registry = get_call_registry()
    # 同期コンテキストから async lookup を呼ぶのは面倒なので、registry の内部 dict を直接見る
    session = None
    for s in registry._sessions.values():  # noqa: SLF001
        if s.meeting_id == meeting_id:
            session = s
            break
    if session is None:
        return

    participants = event_data.get("participants") or event_data.get("Participants") or []
    learned = 0
    for p in participants:
        identifier = (
            p.get("identifier")
            or p.get("Identifier")
            or (p.get("participant") or {}).get("identifier")
            or {}
        )
        raw_id = (
            identifier.get("rawId")
            or identifier.get("raw_id")
            or identifier.get("RawId")
            or ""
        )
        display = (
            p.get("displayName")
            or p.get("DisplayName")
            or p.get("display_name")
            or ""
        )
        if raw_id and display:
            session.participants_by_raw_id[raw_id] = display
            learned += 1
    if learned:
        logger.info(
            "bot.participants_cached",
            meeting_id=meeting_id,
            learned=learned,
            total=len(session.participants_by_raw_id),
        )
