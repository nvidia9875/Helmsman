"""Mock-LLM unit tests for each LLM-backed agent.

`_chat_json` is patched to return fixture dicts so we exercise the parsing /
state-mutation paths without an Azure OpenAI call. The Speech / network paths
are out of scope here.
"""
from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from helmsman.agents import (
    CoverageTracker,
    DecisionCapture,
    DissentSurface,
    GoalDecomposer,
    QuietActivator,
    SteeringAgent,
)
from helmsman.models.meeting import Meeting, MeetingMode, MeetingState
from helmsman.models.participant import Participant
from helmsman.models.topic import Topic, TopicPriority, TopicState
from helmsman.models.utterance import Utterance


def _utterance(speaker_id: str, text: str, sec_ago: int = 0) -> Utterance:
    now = datetime.now(UTC)
    return Utterance(
        meeting_id="m-1",
        speaker_id=speaker_id,
        text=text,
        started_at=now,
        ended_at=now,
        duration_sec=2.0,
    )


def _participant(pid: str, *, total_speak: float = 0.0, count: int = 0) -> Participant:
    return Participant(
        id=pid,
        meeting_id="m-1",
        display_name=pid,
        joined_at=datetime.now(UTC),
        total_speak_seconds=total_speak,
        utterance_count=count,
    )


# ===== GoalDecomposer (T-4) =====


@pytest.mark.asyncio
async def test_goal_decomposer_parses_topics(monkeypatch: pytest.MonkeyPatch) -> None:
    agent = GoalDecomposer()
    fixture = {
        "topics": [
            {
                "name": "技術完成度",
                "decision_criteria": "P0 バグなし",
                "time_budget_pct": 40,
                "priority": "Critical",
                "dependencies": [],
            },
            {
                "name": "マーケ準備",
                "decision_criteria": "LP 公開",
                "time_budget_pct": 60,
                "priority": "Important",
                "dependencies": ["技術完成度"],
            },
        ]
    }
    monkeypatch.setattr(agent, "_chat_json", AsyncMock(return_value=fixture))

    topics = await agent.run("β 版ローンチ", MeetingMode.DECISION)

    assert len(topics) == 2
    assert topics[0].name == "技術完成度"
    assert topics[0].priority == TopicPriority.CRITICAL
    assert topics[0].time_budget_pct == 40
    assert topics[1].dependencies == ["技術完成度"]


@pytest.mark.asyncio
async def test_goal_decomposer_returns_empty_on_bad_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    agent = GoalDecomposer()
    monkeypatch.setattr(agent, "_chat_json", AsyncMock(return_value={}))
    topics = await agent.run("foo", MeetingMode.DECISION)
    assert topics == []


@pytest.mark.asyncio
async def test_goal_decomposer_passes_inherited_topics_to_prompt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """run() should include the inherited topic names somewhere in user_text."""
    agent = GoalDecomposer()
    seen_prompt: list[str] = []

    async def fake_chat_json(prompt: str, **_kw):
        seen_prompt.append(prompt)
        return {"topics": []}

    monkeypatch.setattr(agent, "_chat_json", fake_chat_json)

    inherited = [
        Topic(name="未解決A", decision_criteria="x", time_budget_pct=20)
    ]
    await agent.run("g", MeetingMode.DECISION, inherited_topics=inherited)
    assert any("未解決A" in p for p in seen_prompt)


# ===== CoverageTracker (T-5) =====


@pytest.mark.asyncio
async def test_coverage_tracker_updates_topic_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    agent = CoverageTracker()
    fixture = {
        "topic_updates": [
            {
                "topic_name": "技術完成度",
                "state": "deep_dive",
                "key_speakers": ["田中"],
                "evidence_quote": "P0 バグは 0 件",
                "confidence": 0.9,
                "document_reference": None,
            }
        ]
    }
    monkeypatch.setattr(agent, "_chat_json", AsyncMock(return_value=fixture))

    topics = [
        Topic(name="技術完成度", decision_criteria="P0 0 件", time_budget_pct=40)
    ]
    utterances = [_utterance("u-1", "P0 バグは 0 件です")]
    result = await agent.run(utterances, topics)

    assert result[0].state == TopicState.DEEP_DIVE
    assert result[0].evidence_quote == "P0 バグは 0 件"
    assert result[0].confidence == pytest.approx(0.9)
    assert result[0].key_speakers == ["田中"]


@pytest.mark.asyncio
async def test_coverage_tracker_picks_up_document_reference(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    agent = CoverageTracker()
    monkeypatch.setattr(
        agent,
        "_chat_json",
        AsyncMock(
            return_value={
                "topic_updates": [
                    {
                        "topic_name": "採用基準",
                        "state": "discussing",
                        "confidence": 0.8,
                        "document_reference": "提案書 §3 採用要件",
                    }
                ]
            }
        ),
    )

    topics = [Topic(name="採用基準", decision_criteria="", time_budget_pct=10)]
    out = await agent.run([_utterance("u", "Java 経験 5 年以上")], topics)
    assert out[0].document_reference == "提案書 §3 採用要件"


# ===== SteeringAgent (T-6) =====


@pytest.mark.asyncio
async def test_steering_agent_returns_none_when_on_topic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    agent = SteeringAgent()
    monkeypatch.setattr(
        agent, "_chat_json", AsyncMock(return_value={"detected": False})
    )
    meeting = Meeting(organizer_id="u", goal="g", state=MeetingState.IN_PROGRESS)
    out = await agent.run(meeting, [_utterance("u", "本題")], [])
    assert out is None


# ===== DecisionCapture (T-7) =====


@pytest.mark.asyncio
async def test_decision_capture_marks_topic_decided(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    agent = DecisionCapture()
    monkeypatch.setattr(
        agent,
        "_chat_json",
        AsyncMock(
            return_value={
                "detected": True,
                "topic_name": "ベンダー選定",
                "decision": "A 社で行く",
                "owner": "田中",
                "deadline": "2026-06-30",
                "confidence": 0.85,
                "contradiction_warning": None,
            }
        ),
    )
    meeting = Meeting(
        organizer_id="u", goal="g", state=MeetingState.IN_PROGRESS,
        started_at=datetime.now(UTC),
    )
    topics = [Topic(name="ベンダー選定", decision_criteria="x", time_budget_pct=50)]
    utterances = [
        _utterance("田中", "では A 社で行きましょう"),
        _utterance("佐藤", "了解です"),
    ]
    target, cand = await agent.run(meeting, utterances, topics)
    assert target is not None and target.state == TopicState.DECIDED
    assert cand is not None and "A 社" in cand.content
    assert cand.reason == "decision_captured"


@pytest.mark.asyncio
async def test_decision_capture_flags_contradiction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DOC-6: when contradiction_warning is present, content is prefixed."""
    agent = DecisionCapture()
    monkeypatch.setattr(
        agent,
        "_chat_json",
        AsyncMock(
            return_value={
                "detected": True,
                "topic_name": "ベンダー選定",
                "decision": "B 社で行く",
                "owner": "田中",
                "deadline": "明日",
                "confidence": 0.8,
                "contradiction_warning": "提案書 §2 では A 社のみ承認",
                "contradicted_document": "提案書.pdf",
            }
        ),
    )
    meeting = Meeting(organizer_id="u", goal="g", state=MeetingState.IN_PROGRESS)
    topics = [Topic(name="ベンダー選定", decision_criteria="", time_budget_pct=50)]
    _, cand = await agent.run(
        meeting,
        [_utterance("田中", "B 社で行きましょう"), _utterance("佐藤", "OK")],
        topics,
        document_excerpts="提案書 §2: 承認ベンダーは A 社のみ",
    )
    assert cand is not None
    assert cand.content.startswith("⚠️ 文書と矛盾の可能性")
    assert cand.reason == "decision_contradiction"


# ===== QuietActivator (T-8) =====


@pytest.mark.asyncio
async def test_quiet_activator_returns_none_when_no_quiet_participants(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    agent = QuietActivator()
    # 全員が同じ程度に喋っている = bottom quartile が存在しない
    meeting = Meeting(organizer_id="u", goal="g", state=MeetingState.IN_PROGRESS)
    participants = [_participant(f"u-{i}", total_speak=60, count=10) for i in range(4)]
    topics = [Topic(name="t", decision_criteria="", time_budget_pct=100)]
    # 念のため LLM パスにはモックを (呼ばれた場合に備えて)
    monkeypatch.setattr(
        agent, "_chat_json", AsyncMock(return_value={"detected": False})
    )
    out = await agent.run(meeting, participants, topics)
    assert out is None


# ===== DissentSurface (T-9) =====


@pytest.mark.asyncio
async def test_dissent_surface_skips_when_no_consensus_chain(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    agent = DissentSurface()
    monkeypatch.setattr(
        agent, "_chat_json", AsyncMock(return_value={"detected": False})
    )
    meeting = Meeting(organizer_id="u", goal="g", state=MeetingState.IN_PROGRESS)
    out = await agent.run(meeting, [_utterance("u", "ばらばらの意見")])
    assert out is None
