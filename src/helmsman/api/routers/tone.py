"""Tone (発言感情) API — UI が「話者別 mood + 全体温度感」を polling するエンドポイント。

GET /meetings/{id}/tone : ToneBuffer の集計サマリ全体を返す。
ToneAgent は tick で utterance を分類し buffer に書き込むので、ここでは
ただ buffer を summarize するだけ。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from helmsman.api.security import require_api_key
from helmsman.models.tone import MeetingToneSummary
from helmsman.repositories.meetings import MeetingRepository
from helmsman.services.tone_buffer import get_tone_buffer, summarize

router = APIRouter(
    prefix="/meetings",
    tags=["tone"],
    dependencies=[Depends(require_api_key)],
)


@router.get(
    "/{meeting_id}/tone",
    response_model=MeetingToneSummary,
)
async def get_meeting_tone(meeting_id: str, organizer_id: str) -> MeetingToneSummary:
    """会議全体の感情サマリ — 話者別 mood + 全体 mood + 各発言感情。"""
    meeting = await MeetingRepository().get(meeting_id, organizer_id)
    if meeting is None:
        raise HTTPException(404, "meeting not found")

    buf = get_tone_buffer()
    tones = await buf.get_all(meeting_id)
    return summarize(meeting_id, tones)
