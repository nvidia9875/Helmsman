"""Voiceprint — Azure AI Speech Speaker Recognition プロファイル。"""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from pydantic import BaseModel, Field


class Voiceprint(BaseModel):
    """個人の声紋プロファイル。Entra ID または匿名 ID と紐付ける。"""

    id: str = Field(default_factory=lambda: str(uuid4()))
    entra_id: str | None = None  # Entra ID 連携時のみ
    display_name: str
    speech_profile_id: str  # Azure AI Speech が発行する識別子
    enrolled_at: datetime = Field(default_factory=datetime.utcnow)
    last_used_at: datetime | None = None
    is_active: bool = True
