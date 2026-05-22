"""MemoryRetriever agent — Phase 7 の 9 番目 agent の単体テスト。

embed_texts と search_decisions を mock し、LLM (MINI) 経由の選定ロジックを検証。
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from helmsman.agents.memory_retriever import (
    MEMORY_CONFIDENCE,
    MemoryRetriever,
    _build_query_text,
    _format_intervention_content,
)
from helmsman.core.usage import UsageRecord
from helmsman.models.decision import Decision
from helmsman.models.meeting import Meeting, MeetingMode, MeetingState
from helmsman.models.topic import Topic, TopicPriority, TopicState
from helmsman.models.utterance import Utterance
from helmsman.services.decision_search import DecisionHit


def _meeting(
    *,
    organizer_id: str = "u-1",
    meeting_id: str = "m-current",
    topics: list[Topic] | None = None,
    surfaced_ids: list[str] | None = None,
    series_id: str | None = None,
    group_id: str | None = None,
) -> Meeting:
    return Meeting(
        id=meeting_id,
        organizer_id=organizer_id,
        goal="ローンチ可否",
        mode=MeetingMode.DECISION,
        state=MeetingState.IN_PROGRESS,
        started_at=datetime.now(UTC),
        series_id=series_id,
        group_id=group_id,
        topics=topics or [],
        surfaced_decision_ids=surfaced_ids or [],
    )


def _topic(name: str, state: TopicState = TopicState.DISCUSSING) -> Topic:
    return Topic(
        name=name,
        decision_criteria="P0 バグなし",
        time_budget_pct=30,
        priority=TopicPriority.CRITICAL,
        state=state,
    )


def _utterance(text: str, speaker: str = "s1") -> Utterance:
    now = datetime.now(UTC)
    return Utterance(
        meeting_id="m-current",
        speaker_id=speaker,
        text=text,
        started_at=now,
        ended_at=now + timedelta(seconds=2),
        duration_sec=2.0,
    )


def _decision(
    *,
    decision_id: str,
    meeting_id: str = "m-past",
    topic_name: str = "価格",
    days_ago: int = 7,
    embedding: list[float] | None = None,
) -> Decision:
    return Decision(
        id=decision_id,
        organizer_id="u-1",
        meeting_id=meeting_id,
        topic_id=decision_id.split(":")[1],
        topic_name=topic_name,
        decision_text="¥1200/月で進める",
        owner="田中",
        captured_at=datetime.now(UTC) - timedelta(days=days_ago),
        embedding=embedding or [0.5, 0.5],
    )


# ===== pure helpers =====


def test_build_query_text_includes_topic_and_recent_utterances():
    t = _topic("価格")
    utterances = [_utterance("¥1500だと厳しいです"), _utterance("¥1000なら売れる")]
    out = _build_query_text(t, utterances)
    assert "価格" in out
    assert "決定基準" in out
    assert "¥1500" in out
    assert "¥1000" in out


def test_build_query_text_without_utterances_still_works():
    t = _topic("価格")
    out = _build_query_text(t, [])
    assert "価格" in out
    assert "議論内容" not in out


def test_format_intervention_content_has_date_and_decision():
    d = _decision(decision_id="m-past:t1")
    hit = DecisionHit(decision=d, score=0.9)
    text = _format_intervention_content(hit)
    assert "📜" in text
    assert "価格" in text
    assert "¥1200" in text
    assert "田中" in text


# ===== run() integration with mocks =====


@pytest.mark.asyncio
async def test_run_returns_none_when_no_active_topic(monkeypatch: pytest.MonkeyPatch):
    """全 topic が not_started → 何もしない (LLM 呼ばない)。"""
    m = _meeting(topics=[_topic("価格", state=TopicState.NOT_STARTED)])
    agent = MemoryRetriever()

    # embed が呼ばれないことを spy
    embed_spy = AsyncMock()
    monkeypatch.setattr("helmsman.agents.memory_retriever.embed_texts", embed_spy)

    result = await agent.run(m, recent_utterances=[])
    assert result is None
    embed_spy.assert_not_called()


@pytest.mark.asyncio
async def test_run_returns_none_when_no_search_hits(monkeypatch: pytest.MonkeyPatch):
    """vector search が空 → LLM 呼ばずに skip。"""
    m = _meeting(topics=[_topic("価格")])
    agent = MemoryRetriever()

    monkeypatch.setattr(
        "helmsman.agents.memory_retriever.embed_texts",
        AsyncMock(return_value=([[1.0, 0.0]], None)),
    )
    monkeypatch.setattr(
        "helmsman.agents.memory_retriever.search_decisions",
        AsyncMock(return_value=[]),
    )
    chat_spy = AsyncMock()
    monkeypatch.setattr(agent, "_chat_json", chat_spy)

    result = await agent.run(m, recent_utterances=[])
    assert result is None
    chat_spy.assert_not_called()


@pytest.mark.asyncio
async def test_run_excludes_same_meeting_decisions(monkeypatch: pytest.MonkeyPatch):
    """同一会議で確定した decision は検索結果から除外。"""
    m = _meeting(topics=[_topic("価格")], meeting_id="m-current")
    agent = MemoryRetriever()

    # ヒットは同一会議の decision のみ
    hits = [DecisionHit(decision=_decision(decision_id="m-current:t1", meeting_id="m-current"), score=0.9)]
    monkeypatch.setattr(
        "helmsman.agents.memory_retriever.embed_texts",
        AsyncMock(return_value=([[1.0, 0.0]], None)),
    )
    monkeypatch.setattr(
        "helmsman.agents.memory_retriever.search_decisions",
        AsyncMock(return_value=hits),
    )
    chat_spy = AsyncMock()
    monkeypatch.setattr(agent, "_chat_json", chat_spy)

    result = await agent.run(m, recent_utterances=[])
    assert result is None
    chat_spy.assert_not_called()


@pytest.mark.asyncio
async def test_run_excludes_already_surfaced_decisions(monkeypatch: pytest.MonkeyPatch):
    """surfaced_decision_ids にある decision は除外して dedup。"""
    m = _meeting(
        topics=[_topic("価格")],
        surfaced_ids=["m-past:t1"],
    )
    agent = MemoryRetriever()

    hits = [DecisionHit(decision=_decision(decision_id="m-past:t1"), score=0.9)]
    monkeypatch.setattr(
        "helmsman.agents.memory_retriever.embed_texts",
        AsyncMock(return_value=([[1.0, 0.0]], None)),
    )
    monkeypatch.setattr(
        "helmsman.agents.memory_retriever.search_decisions",
        AsyncMock(return_value=hits),
    )
    chat_spy = AsyncMock()
    monkeypatch.setattr(agent, "_chat_json", chat_spy)

    result = await agent.run(m, recent_utterances=[])
    assert result is None
    chat_spy.assert_not_called()


@pytest.mark.asyncio
async def test_run_produces_candidate_on_llm_yes(monkeypatch: pytest.MonkeyPatch):
    """LLM が selected_index ≥ 0 を返したら candidate 化。"""
    m = _meeting(topics=[_topic("価格")])
    agent = MemoryRetriever()

    past = _decision(decision_id="m-past:t1")
    hits = [DecisionHit(decision=past, score=0.85)]
    monkeypatch.setattr(
        "helmsman.agents.memory_retriever.embed_texts",
        AsyncMock(return_value=([[1.0, 0.0]], None)),
    )
    monkeypatch.setattr(
        "helmsman.agents.memory_retriever.search_decisions",
        AsyncMock(return_value=hits),
    )
    monkeypatch.setattr(
        agent,
        "_chat_json",
        AsyncMock(
            return_value={
                "selected_index": 0,
                "intro_phrase": "前回の会議では",
                "reason": "重複決定",
                "confidence": 0.9,
            }
        ),
    )

    result = await agent.run(m, recent_utterances=[_utterance("価格をどうしましょう")])
    assert result is not None
    assert result.agent == "MemoryRetriever"
    assert result.confidence == MEMORY_CONFIDENCE
    assert result.reason == "cross_meeting_recall"
    assert "価格" in result.content
    assert result.evidence_quote == "m-past:t1"


@pytest.mark.asyncio
async def test_run_returns_none_when_llm_says_minus_one(monkeypatch: pytest.MonkeyPatch):
    """LLM が selected_index=-1 (該当なし) → None。"""
    m = _meeting(topics=[_topic("価格")])
    agent = MemoryRetriever()

    hits = [DecisionHit(decision=_decision(decision_id="m-past:t1"), score=0.85)]
    monkeypatch.setattr(
        "helmsman.agents.memory_retriever.embed_texts",
        AsyncMock(return_value=([[1.0, 0.0]], None)),
    )
    monkeypatch.setattr(
        "helmsman.agents.memory_retriever.search_decisions",
        AsyncMock(return_value=hits),
    )
    monkeypatch.setattr(
        agent,
        "_chat_json",
        AsyncMock(return_value={"selected_index": -1, "confidence": 0.9}),
    )

    result = await agent.run(m, recent_utterances=[])
    assert result is None


@pytest.mark.asyncio
async def test_run_returns_none_when_llm_low_confidence(monkeypatch: pytest.MonkeyPatch):
    """LLM confidence < 0.6 → 該当扱いしない。"""
    m = _meeting(topics=[_topic("価格")])
    agent = MemoryRetriever()

    hits = [DecisionHit(decision=_decision(decision_id="m-past:t1"), score=0.85)]
    monkeypatch.setattr(
        "helmsman.agents.memory_retriever.embed_texts",
        AsyncMock(return_value=([[1.0, 0.0]], None)),
    )
    monkeypatch.setattr(
        "helmsman.agents.memory_retriever.search_decisions",
        AsyncMock(return_value=hits),
    )
    monkeypatch.setattr(
        agent,
        "_chat_json",
        AsyncMock(return_value={"selected_index": 0, "confidence": 0.5}),
    )

    result = await agent.run(m, recent_utterances=[])
    assert result is None


@pytest.mark.asyncio
async def test_run_prefers_deep_dive_over_discussing(monkeypatch: pytest.MonkeyPatch):
    """deep_dive 状態の topic が discussing より優先。"""
    discussing = _topic("価格", state=TopicState.DISCUSSING)
    deep = _topic("リスク", state=TopicState.DEEP_DIVE)
    m = _meeting(topics=[discussing, deep])

    captured_query: list[str] = []

    async def fake_embed(texts: list[str]):
        captured_query.extend(texts)
        return [[1.0, 0.0]], None

    monkeypatch.setattr("helmsman.agents.memory_retriever.embed_texts", fake_embed)
    monkeypatch.setattr(
        "helmsman.agents.memory_retriever.search_decisions",
        AsyncMock(return_value=[]),
    )

    await MemoryRetriever().run(m, recent_utterances=[])
    assert any("リスク" in q for q in captured_query)
    assert not any("価格" in q for q in captured_query)


@pytest.mark.asyncio
async def test_run_applies_embed_usage_to_sink(monkeypatch: pytest.MonkeyPatch):
    """embed の usage が sink に集計される (コスト追跡)。"""
    from helmsman.core.usage import MeetingUsage

    m = _meeting(topics=[_topic("価格")])
    agent = MemoryRetriever()
    sink = MeetingUsage()

    usage = UsageRecord(
        agent_name="EmbeddingService",
        model_deployment="text-embedding-3-small",
        prompt_tokens=10,
        completion_tokens=0,
        total_tokens=10,
    )
    monkeypatch.setattr(
        "helmsman.agents.memory_retriever.embed_texts",
        AsyncMock(return_value=([[1.0, 0.0]], usage)),
    )
    monkeypatch.setattr(
        "helmsman.agents.memory_retriever.search_decisions",
        AsyncMock(return_value=[]),
    )

    await agent.run(m, recent_utterances=[], usage_sink=sink)
    assert sink.total_tokens == 10


@pytest.mark.asyncio
async def test_run_passes_series_and_group_to_search(monkeypatch: pytest.MonkeyPatch):
    """search_decisions に series_id / group_id が渡る (boost 用)。"""
    m = _meeting(
        topics=[_topic("価格")],
        series_id="s-weekly",
        group_id="g-launch",
    )
    monkeypatch.setattr(
        "helmsman.agents.memory_retriever.embed_texts",
        AsyncMock(return_value=([[1.0, 0.0]], None)),
    )
    search_spy = AsyncMock(return_value=[])
    monkeypatch.setattr("helmsman.agents.memory_retriever.search_decisions", search_spy)

    await MemoryRetriever().run(m, recent_utterances=[])
    kwargs = search_spy.call_args.kwargs
    assert kwargs["series_id"] == "s-weekly"
    assert kwargs["group_id"] == "g-launch"
    assert kwargs["organizer_id"] == "u-1"
