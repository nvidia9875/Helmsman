"""MeetingReport — 生成済みレポートの永続化モデル。

Cosmos `meeting_reports` (partition key = /meeting_id) に格納。
1 会議で複数回生成可能 (テンプレ違いやメモ追記でやり直す)。
履歴として残し、UI で最新版と過去版を切り替えられるようにする。
"""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from pydantic import BaseModel, Field

from helmsman.core.usage import UsageRecord


class MeetingReport(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    meeting_id: str
    organizer_id: str
    report_markdown: str

    template_used: bool = False
    memo_used: bool = False
    utterances_included: int = 0

    # 生成時に投入したテンプレ/メモ自体も残す (再現性 + 監査)
    template_snapshot: str | None = None
    memo_snapshot: str | None = None

    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    generator_agent: str = "MeetingReportGenerator"
    generator_model: str | None = None
    usage: UsageRecord | None = None
