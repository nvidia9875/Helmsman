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
from datetime import UTC, datetime
from typing import Any

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    status,
)
from pydantic import BaseModel, Field

from helmsman.api.security import require_api_key
from helmsman.core.logging import logger
from helmsman.models.meeting import Meeting
from helmsman.repositories.meetings import MeetingRepository
from helmsman.services.call_buffer import (
    get_call_registry,
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
    if not session:
        raise HTTPException(
            409,
            "bot is not in a call right now — invite the bot to a Teams meeting first",
        )

    # ACS / Graph いずれの経路でも対応
    if session.media_ws is not None:
        from helmsman.services.tts import speak_into_call
        asyncio.create_task(speak_into_call(session.media_ws, req.text))
    else:
        from helmsman.services.graph_play_prompt import play_text_in_graph_call
        asyncio.create_task(
            play_text_in_graph_call(session.call_connection_id, req.text)
        )
    logger.info(
        "bot.manual_speak",
        meeting_id=meeting_id,
        text=req.text[:80],
        path="ws" if session.media_ws is not None else "graph",
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
    repo: MeetingRepository = Depends(get_repo),
) -> BotTranscriptResponse:
    """Bot がリアルタイムで拾った発言の一覧。

    Bot が active な間は in-memory CallSession のバッファを返す (リアルタイム)。
    Bot disconnect 後は Cosmos に永続化された `meeting.transcript` を fallback で返す
    (会議終了後の参照 / レポート生成のため)。
    """
    registry = get_call_registry()
    session = await registry.lookup_by_meeting(meeting_id)
    if session:
        # Bot active: in-memory バッファを返す
        tail = session.utterances[-limit:]
        return BotTranscriptResponse(
            bot_active=True,
            utterance_count=len(session.utterances),
            utterances=[u.model_dump(mode="json") for u in tail],
        )

    # Bot disconnected: Cosmos の永続化 transcript を fallback で返す
    meeting = await repo.get(meeting_id, organizer_id)
    if not meeting or not meeting.transcript:
        return BotTranscriptResponse(bot_active=False, utterance_count=0, utterances=[])
    tail = meeting.transcript[-limit:]
    return BotTranscriptResponse(
        bot_active=False,
        utterance_count=len(meeting.transcript),
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



# ---------- Microsoft Graph Communications webhook (no auth) ----------


def _count_human_participants(participants: list[Any]) -> int:
    """Graph participants 配列から human (= bot 以外) の数を数える。

    Participant の identity スキーマ揺れに対する防御:
    - identity.user.id がある → human
    - identity.application.id がある → application (bot 等) → 除外
    - identity.guest.id がある → human (anonymous external user)
    """
    from helmsman.core.config import get_settings

    settings = get_settings()
    bot_app_id = (settings.microsoft_app_id or "").lower()

    count = 0
    for p in participants:
        if not isinstance(p, dict):
            continue
        info = p.get("info") or {}
        identity = info.get("identity") or p.get("identity") or {}
        if not isinstance(identity, dict):
            continue
        # user or guest が居れば human としてカウント
        if identity.get("user") or identity.get("guest"):
            count += 1
            continue
        # application で自分の bot app id なら除外。
        # 他の bot は human 扱いにする (誤判定回避)
        app = identity.get("application") or {}
        if isinstance(app, dict):
            app_id = (app.get("id") or "").lower()
            if app_id and app_id != bot_app_id:
                count += 1
    return count




# Graph call state → Helmsman bot_status マッピング
# https://learn.microsoft.com/graph/api/resources/call (state プロパティ)
_STATUS_BY_GRAPH_STATE = {
    "incoming": "connecting",
    "establishing": "connecting",
    "established": "in_call",
    "hold": "in_call",
    "transferring": "in_call",
    "redirecting": "in_call",
    "terminating": "disconnected",
    "terminated": "disconnected",
}


@router.post("/api/calling", status_code=status.HTTP_200_OK)
async def graph_calling_callback(
    request: Request,
    repo: MeetingRepository = Depends(get_repo),
) -> dict[str, Any]:
    """Microsoft Graph Communications API からの notification webhook。

    POST body 形式 (https://learn.microsoft.com/graph/api/resources/commsnotifications):
    ```
    {
      "@odata.type": "#microsoft.graph.commsNotifications",
      "value": [
        {
          "@odata.type": "#microsoft.graph.commsNotification",
          "changeType": "updated",
          "resourceUrl": "/communications/calls/{id}",
          "resourceData": {
            "@odata.type": "#microsoft.graph.call",
            "state": "established",
            "operationContext": "meeting:m-xxx|org:u-yyy"
          }
        }
      ]
    }
    ```

    認証: Microsoft が Bot Framework JWT 付きで POST してくる。本番では JWT 検証推奨だが
    ハッカソン期間は public endpoint として運用 (rate limit のみ Container App 側で制御)。
    """
    payload = await request.json()

    # payload は dict or list で来うる (Graph 仕様の揺れ)。両対応。
    if isinstance(payload, dict):
        notifications = payload.get("value") or []
    elif isinstance(payload, list):
        notifications = payload
    else:
        notifications = []
    if not isinstance(notifications, list):
        notifications = []

    handled = 0
    for notif in notifications:
        # notif 自体が dict 以外の可能性に対する防御
        if not isinstance(notif, dict):
            continue

        change_type = notif.get("changeType", "")
        resource_url = notif.get("resourceUrl") or notif.get("resource") or ""
        resource_data = notif.get("resourceData") or {}
        if not isinstance(resource_data, dict):
            resource_data = {}

        # operationContext は call の作成時に設定したもの。
        # ただし Microsoft は state 変更通知で echo back しないケースあり → call_id で fallback。
        op_ctx = resource_data.get("operationContext") or notif.get("operationContext")
        meeting_id, organizer_id = parse_operation_context(op_ctx)

        call_state = resource_data.get("state", "")
        # resource_url 例:
        #   /communications/calls/{id}                            ← state 変更
        #   /communications/calls/{id}/operations/{opId}          ← operation 完了 (録音等)
        #   /communications/calls/{id}/participants               ← 参加者更新
        # URL から call_id を必ず取り出す。resource_data.id は operation/participant では
        # call_id ではなく opId 等になるため URL を優先する。
        call_id = ""
        operation_id = ""
        if isinstance(resource_url, str):
            import re as _re
            _m_call = _re.search(r"/communications/calls/([^/]+)", resource_url)
            if _m_call:
                call_id = _m_call.group(1)
            _m_op = _re.search(r"/operations/([^/?]+)", resource_url)
            if _m_op:
                operation_id = _m_op.group(1)
        # フォールバック: state 変更 event なら resource_data.id が call_id
        if not call_id and not operation_id:
            call_id = resource_data.get("id") or ""

        # /operations/{id} は recordOperationCompleted 等の operation 完了通知。
        is_operation_event = bool(operation_id)
        if is_operation_event:
            odata_type = resource_data.get("@odata.type", "")
            op_status = resource_data.get("status", "")
            recording_location = resource_data.get("recordingLocation") or resource_data.get(
                "resultInfo", {}
            ).get("recordingLocation")
            logger.info(
                "graph.operation",
                call_id=call_id,
                operation_id=operation_id,
                odata_type=odata_type,
                op_status=op_status,
                has_recording_location=bool(recording_location),
                resource_url=resource_url,
            )

            # playPromptOperation completed → 即 recording loop resume
            # (auto_resume fallback タイマーよりも正確)
            if (
                "playPromptOperation" in odata_type
                and op_status == "completed"
                and call_id
            ):
                from helmsman.services.recording_loop import resume_recording_after_tts
                resume_recording_after_tts(call_id)
                logger.info(
                    "graph_tts.resumed_via_webhook",
                    call_id=call_id,
                    op_id=operation_id,
                )
            # recordOperationCompleted で recordingLocation あり → STT に流す
            if (
                "recordOperation" in odata_type
                and op_status == "completed"
                and recording_location
                and call_id
            ):
                from helmsman.services.recording_loop import get_recording_meta
                rec_meeting_id, rec_organizer_id = get_recording_meta(call_id)
                access_token = (
                    resource_data.get("recordingAccessToken")
                    or resource_data.get("resultInfo", {}).get("recordingAccessToken")
                )
                logger.info(
                    "graph.recording_ready",
                    call_id=call_id,
                    operation_id=operation_id,
                    meeting_id=rec_meeting_id,
                    organizer_id=rec_organizer_id,
                    has_token=bool(access_token),
                    location=recording_location[:120],
                )
                if rec_meeting_id and rec_organizer_id:
                    # fire-and-forget: download + STT は時間かかるので背景タスク化
                    from helmsman.services.recording_stt import transcribe_and_dispatch
                    asyncio.create_task(
                        transcribe_and_dispatch(
                            call_id=call_id,
                            meeting_id=rec_meeting_id,
                            organizer_id=rec_organizer_id,
                            recording_url=recording_location,
                            access_token=access_token,
                        )
                    )
            handled += 1
            continue

        # /participants サブパスへの notification は participant 一覧の更新。
        # human 参加者ゼロになったら Teams 会議終了 ≒ 自動 hangup する。
        is_participants_event = isinstance(resource_url, str) and resource_url.endswith(
            "/participants"
        )
        if is_participants_event and call_id:
            participants = notif.get("resourceData")
            if isinstance(participants, dict):
                participants = participants.get("value") or []
            if not isinstance(participants, list):
                participants = []
            human_count = _count_human_participants(participants)
            logger.info(
                "graph.participants",
                call_id=call_id,
                count=len(participants),
                human_count=human_count,
            )
            if human_count == 0:
                logger.info(
                    "graph.auto_hangup",
                    call_id=call_id,
                    reason="no_human_participants",
                )
                try:
                    from helmsman.services.graph_calling import hangup_via_graph
                    await hangup_via_graph(call_id)
                except Exception as e:  # noqa: BLE001
                    logger.warning(
                        "graph.auto_hangup_failed",
                        call_id=call_id,
                        error=str(e),
                    )
            handled += 1
            continue

        # fallback: registry から call_id で meeting を引く
        if not (meeting_id and organizer_id) and call_id:
            from helmsman.services.graph_calling import lookup_call
            fb_meeting_id, fb_organizer_id = lookup_call(call_id)
            if fb_meeting_id and fb_organizer_id:
                meeting_id, organizer_id = fb_meeting_id, fb_organizer_id

        logger.info(
            "graph.event",
            change_type=change_type,
            call_state=call_state,
            call_id=call_id,
            meeting_id=meeting_id,
            organizer_id=organizer_id,
            resource_url=resource_url,
        )

        if not (meeting_id and organizer_id):
            # operationContext も registry も無い event はスキップ
            continue

        meeting = await repo.get(meeting_id, organizer_id)
        if not meeting:
            logger.warning(
                "graph.event_unknown_meeting",
                meeting_id=meeting_id,
                organizer_id=organizer_id,
            )
            continue

        meeting.bot_last_event_at = datetime.now(UTC)
        # call_id は graph_calling.py が返した値と同じはず。記録しておく。
        if call_id and not meeting.bot_call_connection_id:
            meeting.bot_call_connection_id = call_id

        new_status = _STATUS_BY_GRAPH_STATE.get(call_state)
        if new_status is not None:
            meeting.bot_status = new_status
            if new_status == "disconnected":
                meeting.bot_call_connection_id = None

        # changeType=deleted は call が消えた = 確実に disconnected
        if change_type == "deleted":
            meeting.bot_status = "disconnected"
            meeting.bot_call_connection_id = None

        # call established → 録音ループ開始 (idempotent)
        if call_state == "established" and call_id and meeting_id and organizer_id:
            from helmsman.services.recording_loop import start_recording
            start_recording(call_id, meeting_id, organizer_id)
            # 入室挨拶を会議チャットに投稿(初回のみ)。チャット投稿の疎通確認も兼ねる。
            # NOTE: chat_greeted は投稿成功後にのみ立てる。先に立てると 1 回失敗した
            # だけで二度と挨拶しなくなる (リトライ不能バグ) ため。
            if meeting.chat_post_enabled and not meeting.chat_greeted:
                from helmsman.services.graph_calling import (
                    post_meeting_chat_message,
                    resolve_thread_id,
                )
                tid = meeting.chat_thread_id
                if not tid and meeting.teams_meeting_url:
                    tid = await resolve_thread_id(meeting.teams_meeting_url)
                    meeting.chat_thread_id = tid
                if tid:
                    name = meeting.facilitator_name or "Helmsman"
                    greeting = (
                        f"<b>🧭 {name}</b><br>こんにちは。"
                        "この会議のファシリテーターとして参加しました。"
                        "議論の要点や決定はこのチャットにも書き込みます。"
                    )
                    try:
                        await post_meeting_chat_message(tid, greeting)
                        meeting.chat_greeted = True
                    except Exception as e:  # noqa: BLE001
                        # 投稿失敗時はフラグを立てず、次の established イベントで再試行する
                        logger.warning(
                            "graph.greeting_post_failed",
                            meeting_id=meeting_id,
                            thread_id=tid,
                            error=str(e),
                        )
                else:
                    logger.warning(
                        "graph.greeting_no_thread_id",
                        meeting_id=meeting_id,
                        teams_meeting_url=meeting.teams_meeting_url,
                    )

        # disconnected になったら call registry + 録音 + CallSession 全部削除
        if meeting.bot_status == "disconnected" and call_id:
            from helmsman.services.graph_calling import unregister_call
            from helmsman.services.recording_loop import stop_recording
            unregister_call(call_id)
            stop_recording(call_id)
            # CallSession (call_buffer) からも削除 → lookup_by_meeting が古い call_id を返さない
            try:
                await get_call_registry().drop(call_id)
            except Exception as e:  # noqa: BLE001
                logger.warning(
                    "graph.session_drop_failed", call_id=call_id, error=str(e)
                )

        await repo.upsert(meeting)
        handled += 1

    return {"handled": handled}


@router.post("/api/messages", status_code=status.HTTP_200_OK)
async def bot_framework_messages(request: Request) -> dict[str, Any]:
    """Bot Framework メッセージング webhook (Teams チャット bot 用、Phase D で使う)。

    現状は no-op (受信して 200 を返すだけ)。Phase D で Teams app からの
    1:1 chat / adaptive card メッセージを処理する予定。
    """
    try:
        body = await request.json()
        logger.info(
            "bot.framework_message",
            activity_type=body.get("type"),
            from_id=(body.get("from") or {}).get("id", ""),
        )
    except Exception:  # noqa: BLE001
        # body が JSON でない / 空 — health check の可能性
        pass
    return {"ok": True}
