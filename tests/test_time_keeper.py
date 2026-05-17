"""TimeKeeper (ルールベース) のテスト。"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from helmsman.agents.time_keeper import TimeKeeper
from helmsman.models.topic import TopicPriority, TopicState


def test_returns_none_when_time_remaining(meeting):
    """時間に余裕がある時は何も返さない。"""
    meeting.started_at = datetime.now(UTC) - timedelta(minutes=10)  # 残り 83%
    assert TimeKeeper().run(meeting) is None


def test_alerts_when_critical_unfinished_below_30pct(meeting):
    """残り 30% 未満で Critical 論点が未着手なら警告。"""
    meeting.started_at = datetime.now(UTC) - timedelta(minutes=45)  # 残り 25%
    cand = TimeKeeper().run(meeting)
    assert cand is not None
    assert cand.reason == "critical_unfinished"
    assert cand.confidence >= 0.9


def test_alerts_when_time_almost_up(meeting):
    """残り 20% 未満なら任意の未着手論点で警告。"""
    # 残り 17%, Critical を全て decided にして Optional だけ未着手の状態を作る
    for t in meeting.topics:
        if t.priority != TopicPriority.OPTIONAL:
            t.state = TopicState.DECIDED
    meeting.started_at = datetime.now(UTC) - timedelta(minutes=50)
    cand = TimeKeeper().run(meeting)
    assert cand is not None
    assert cand.reason == "time_almost_up"


def test_returns_none_when_meeting_not_started(meeting):
    """会議開始前は time_remaining=1.0 なので何も警告しない。"""
    meeting.started_at = None
    assert TimeKeeper().run(meeting) is None
