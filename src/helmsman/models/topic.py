"""Topic (論点) — Goal Decomposer が生成し Coverage Tracker が状態を更新する。"""
from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field


class TopicPriority(str, Enum):
    CRITICAL = "Critical"
    IMPORTANT = "Important"
    OPTIONAL = "Optional"


class TopicState(str, Enum):
    NOT_STARTED = "not_started"   # 未着手
    DISCUSSING = "discussing"      # 議論中
    DEEP_DIVE = "deep_dive"        # 深掘り済
    DECIDED = "decided"            # 決定済


class Topic(BaseModel):
    """会議の論点 1 つ。Coverage Tracker がリアルタイム状態を更新する。"""

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str = Field(..., description="論点名 (10字以内が望ましい)")
    decision_criteria: str = Field(..., description="「決定済」とみなす条件")
    time_budget_pct: float = Field(..., ge=0, le=100, description="全体時間に対する割合")
    priority: TopicPriority = TopicPriority.IMPORTANT
    dependencies: list[str] = Field(default_factory=list, description="先行論点 ID")

    # Live state
    state: TopicState = TopicState.NOT_STARTED
    last_mention_at: datetime | None = None
    key_speakers: list[str] = Field(default_factory=list)
    evidence_quote: str | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    # 文書 RAG: Coverage Tracker が会議内容と関連付けた文書箇所 (例: "提案書 §3 採用要件")
    document_reference: str | None = None
