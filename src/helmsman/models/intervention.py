"""Intervention — 各 Agent が提案する介入候補と最終配信。"""
from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field


class InterventionLevel(str, Enum):
    """介入強度。Arbiter が決定する。

    L1: 司会者のみに Whisper (subtle)
    L2: 全員のサイドバーにカード表示 (visible)
    L3: 音声で発話 (loud) — gpt-realtime + TTS
    """

    L1 = "L1"
    L2 = "L2"
    L3 = "L3"


class InterventionCandidate(BaseModel):
    """Agent が Arbiter に投げる候補。"""

    id: str = Field(default_factory=lambda: str(uuid4()))
    meeting_id: str
    agent: str  # "GoalDecomposer" / "CoverageTracker" / ... / "Arbiter"
    content: str
    reason: str
    evidence_quote: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    allowed_modes: list[str] = Field(default_factory=list)  # 空ならすべてのモードで許可


class InterventionDelivery(BaseModel):
    """Arbiter が最終決定した配信。"""

    id: str = Field(default_factory=lambda: str(uuid4()))
    meeting_id: str
    candidate_id: str
    agent: str
    content: str
    reason: str
    evidence_quote: str | None = None
    level: InterventionLevel
    audience: list[str]  # ["chair"] / ["all"] / ["room_speaker", "remote_audio_inject"]
    delivered_at: datetime = Field(default_factory=datetime.utcnow)
