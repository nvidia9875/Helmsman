"""Utterance — 発言ストリームの 1 単位。"""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from pydantic import BaseModel, Field


class Utterance(BaseModel):
    """STT が認識した 1 発言 (1〜30秒程度の chunk)。"""

    id: str = Field(default_factory=lambda: str(uuid4()))
    meeting_id: str
    speaker_id: str  # participant.id または "unknown"
    text: str
    started_at: datetime
    ended_at: datetime
    duration_sec: float
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    is_final: bool = True  # ストリーム中の interim を区別

    @property
    def length_sec(self) -> float:
        return (self.ended_at - self.started_at).total_seconds()
