"""Participant — 会議参加者。"""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from pydantic import BaseModel, Field


class Participant(BaseModel):
    """会議参加者。Entra ID 連携または匿名 ID。"""

    id: str = Field(default_factory=lambda: str(uuid4()))
    meeting_id: str
    display_name: str
    entra_id: str | None = None  # Entra ID 認証時のみ
    voiceprint_profile_id: str | None = None  # Speaker Recognition 連携
    is_chair: bool = False
    is_senior: bool = False  # Authority gradient 用 (上司発言中は介入弱める)
    joined_at: datetime = Field(default_factory=datetime.utcnow)

    # Live stats
    total_speak_seconds: float = 0.0
    utterance_count: int = 0
