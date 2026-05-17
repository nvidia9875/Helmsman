"""MeetingGroup — 複数会議を束ねる「グループ」エンティティ。

シリーズ (parent_meeting_id チェーンで自動形成) とは別に、
ユーザーが手動でプロジェクト単位で会議を束ねたいケースに使う。
グループ配下の文書は配下全会議の RAG に流れる。
"""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from pydantic import BaseModel, Field


class MeetingGroup(BaseModel):
    """会議グループ。Cosmos `groups` コンテナ (partition: /organizer_id)。"""

    id: str = Field(default_factory=lambda: str(uuid4()))
    organizer_id: str
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=600)

    # 視覚識別用 (UI でバッジ色などに使用)
    accent_hex: str | None = None

    document_ids: list[str] = Field(default_factory=list)
    meeting_ids: list[str] = Field(default_factory=list)

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def touch(self) -> None:
        """updated_at を現在時刻に更新 (in-place ではなく明示的に呼ぶ)。"""
        self.updated_at = datetime.now(UTC)
