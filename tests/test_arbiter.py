"""Arbiter (新規性の核) のルールベーステスト。LLM 呼び出しなし。"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from helmsman.agents.arbiter import InterventionArbiter
from helmsman.models.intervention import InterventionCandidate, InterventionLevel
from helmsman.models.meeting import Meeting, UserIntensity
from helmsman.models.participant import Participant


def _candidate(agent: str, confidence: float = 0.9, content: str = "x") -> InterventionCandidate:
    return InterventionCandidate(
        meeting_id="m1",
        agent=agent,
        content=content,
        reason="test",
        confidence=confidence,
    )


def _participant(name: str = "p1", senior: bool = False) -> Participant:
    return Participant(meeting_id="m1", display_name=name, is_senior=senior)


@pytest.fixture
def arbiter() -> InterventionArbiter:
    return InterventionArbiter()


def test_no_candidates_returns_none(arbiter, meeting):
    assert arbiter.decide([], meeting, None, None) is None


def test_low_confidence_is_filtered(arbiter, meeting):
    low = _candidate("DecisionCapture", confidence=0.5)
    assert arbiter.decide([low], meeting, None, None) is None


def test_decision_capture_has_highest_priority(arbiter, meeting):
    candidates = [
        _candidate("QuietActivator"),
        _candidate("DecisionCapture"),
        _candidate("SteeringAgent"),
    ]
    d = arbiter.decide(candidates, meeting, None, None)
    assert d is not None
    assert d.agent == "DecisionCapture"


def test_l3_only_when_high_priority_and_time_nearly_up(arbiter, meeting):
    """time_left < 0.20 + priority>=80 → L3"""
    meeting.started_at = datetime.now(UTC) - timedelta(minutes=55)  # 残り <10%
    c = _candidate("TimeKeeper")  # priority 80
    d = arbiter.decide([c], meeting, None, None)
    assert d is not None
    assert d.level == InterventionLevel.L3


def test_l2_for_mid_priority(arbiter, meeting):
    """priority 50-79 → L2"""
    meeting.started_at = datetime.now(UTC) - timedelta(minutes=10)  # 残り 83%
    c = _candidate("SteeringAgent")  # priority 70
    d = arbiter.decide([c], meeting, None, None)
    assert d is not None
    assert d.level == InterventionLevel.L2


def test_l1_for_low_priority(arbiter, meeting):
    """priority < 50 → L1 (AGGRESSIVE 設定下では下位 priority も通る)"""
    meeting.user_intensity = UserIntensity.AGGRESSIVE
    meeting.started_at = datetime.now(UTC) - timedelta(minutes=10)
    c = _candidate("GoalDecomposer")  # priority 30
    d = arbiter.decide([c], meeting, None, None)
    assert d is not None
    assert d.level == InterventionLevel.L1


def test_rate_limit_blocks_subsequent_interventions(arbiter, meeting):
    """直近 60 秒以内に介入があれば、低優先度は通さない。"""
    meeting.last_intervention_at = datetime.now(UTC) - timedelta(seconds=10)
    c = _candidate("QuietActivator")  # priority 50, rate_limit 60s
    assert arbiter.decide([c], meeting, None, None) is None


def test_high_priority_has_shorter_rate_limit(arbiter, meeting):
    """priority>=80 は 20 秒の rate limit に短縮される。"""
    meeting.last_intervention_at = datetime.now(UTC) - timedelta(seconds=25)
    c = _candidate("DecisionCapture")  # priority 100, rate_limit 20s
    d = arbiter.decide([c], meeting, None, None)
    assert d is not None


def test_density_aware_silence_blocks_low_priority(arbiter, meeting):
    """議論密度が高い時 (>0.8) は低優先度を抑制する。"""
    meeting.recent_utterance_density = 0.9
    c = _candidate("QuietActivator")  # priority 50
    assert arbiter.decide([c], meeting, None, None) is None


def test_density_aware_silence_allows_high_priority(arbiter, meeting):
    """高優先度 (>=80) は density に関係なく通す。"""
    meeting.recent_utterance_density = 0.95
    c = _candidate("DecisionCapture")
    assert arbiter.decide([c], meeting, None, None) is not None


def test_authority_gradient_suppresses_low_priority_when_senior_speaks(arbiter, meeting):
    """上司発言中 (senior=True) は priority<70 を抑制する。"""
    senior = _participant(senior=True)
    c = _candidate("QuietActivator")  # priority 50
    assert arbiter.decide([c], meeting, None, senior) is None


def test_authority_gradient_allows_critical_during_senior(arbiter, meeting):
    """上司発言中でも priority>=70 (Steering 以上) は通す。"""
    senior = _participant(senior=True)
    c = _candidate("SteeringAgent")  # priority 70
    assert arbiter.decide([c], meeting, None, senior) is not None


def test_user_intensity_quiet_blocks_below_80(arbiter, meeting):
    """user_intensity=quiet → priority<80 は通さない。"""
    meeting.user_intensity = UserIntensity.QUIET
    c = _candidate("SteeringAgent")  # priority 70
    assert arbiter.decide([c], meeting, None, None) is None
    c2 = _candidate("DecisionCapture")  # priority 100
    assert arbiter.decide([c2], meeting, None, None) is not None


def test_user_intensity_aggressive_allows_all(arbiter, meeting):
    """user_intensity=aggressive → 全て通す。"""
    meeting.user_intensity = UserIntensity.AGGRESSIVE
    c = _candidate("GoalDecomposer")  # priority 30
    assert arbiter.decide([c], meeting, None, None) is not None


def test_l1_audience_is_chair_only(arbiter, meeting):
    """AGGRESSIVE 設定下で L1 介入は司会者のみに配信。"""
    meeting.user_intensity = UserIntensity.AGGRESSIVE
    chair = _participant("chair-user")
    meeting.started_at = datetime.now(UTC) - timedelta(minutes=10)
    c = _candidate("GoalDecomposer")  # L1
    d = arbiter.decide([c], meeting, chair, None)
    assert d is not None
    assert d.audience == [chair.id]


def test_l2_audience_is_all(arbiter, meeting):
    meeting.started_at = datetime.now(UTC) - timedelta(minutes=10)
    c = _candidate("SteeringAgent")  # L2
    d = arbiter.decide([c], meeting, None, None)
    assert d is not None
    assert d.audience == ["all"]
