"""Helmsman Bot endpoints — Teams 会議への招待 + ACS Call Automation webhook 受け口。

Flow:
  1. UI が POST /meetings/{id}/bot/invite {teams_meeting_url}
  2. Helmsman → ACS Call Automation: connect_call(teams meeting locator)
  3. ACS → 会議に Helmsman (External) として参加
  4. ACS → POST {callback_base}/bot/callback (CallConnected / CallDisconnected 等)
  5. それを Meeting.bot_status に反映 + Cosmos に永続化
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from helmsman.api.security import require_api_key
from helmsman.core.logging import logger
from helmsman.models.meeting import Meeting
from helmsman.repositories.meetings import MeetingRepository
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
        handled += 1

    return {"handled": handled}
