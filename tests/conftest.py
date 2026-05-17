"""Shared pytest fixtures for Helmsman test suite."""
from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta

import pytest

# .env を読まないように一旦最小限の必須変数を埋める (Settings の validation 用)
os.environ.setdefault("AZURE_OPENAI_ENDPOINT", "https://example.openai.azure.com/")
os.environ.setdefault("AZURE_OPENAI_API_KEY", "dummy")
os.environ.setdefault("COSMOS_ENDPOINT", "https://example.documents.azure.com:443/")
os.environ.setdefault("COSMOS_KEY", "dummy")


@pytest.fixture
def utc_now() -> datetime:
    return datetime.now(UTC)


@pytest.fixture
def past(utc_now: datetime) -> datetime:
    return utc_now - timedelta(minutes=10)


@pytest.fixture
def meeting():
    """Decision モードの 60 分会議 (5 論点)。"""
    from helmsman.models.meeting import Meeting, MeetingMode, MeetingState
    from helmsman.models.topic import Topic, TopicPriority, TopicState

    return Meeting(
        organizer_id="u-test",
        goal="ローンチ可否を決定する",
        mode=MeetingMode.DECISION,
        total_minutes=60,
        state=MeetingState.IN_PROGRESS,
        started_at=datetime.now(UTC) - timedelta(minutes=50),  # 残り 17%
        topics=[
            Topic(
                name="技術完成度", decision_criteria="P0 バグなし",
                time_budget_pct=30, priority=TopicPriority.CRITICAL,
            ),
            Topic(
                name="マーケ準備", decision_criteria="LP 公開",
                time_budget_pct=20, priority=TopicPriority.IMPORTANT,
                state=TopicState.DECIDED,
            ),
            Topic(
                name="リスク評価", decision_criteria="3 リスク特定",
                time_budget_pct=25, priority=TopicPriority.CRITICAL,
            ),
            Topic(
                name="サポート体制", decision_criteria="窓口決定",
                time_budget_pct=15, priority=TopicPriority.IMPORTANT,
            ),
            Topic(
                name="撤退基準", decision_criteria="閾値合意",
                time_budget_pct=10, priority=TopicPriority.OPTIONAL,
            ),
        ],
    )
