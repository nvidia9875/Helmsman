"""decision_persistence.persist_decision — write-through 永続化フックのテスト。"""
from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from helmsman.core.usage import MeetingUsage, UsageRecord
from helmsman.models.intervention import InterventionCandidate
from helmsman.models.meeting import Meeting, MeetingMode, MeetingState
from helmsman.models.topic import Topic, TopicPriority, TopicState


def _meeting(
    *, series_id: str | None = None, group_id: str | None = None
) -> Meeting:
    return Meeting(
        id="m-current",
        organizer_id="u-1",
        goal="ローンチ",
        mode=MeetingMode.DECISION,
        state=MeetingState.IN_PROGRESS,
        started_at=datetime.now(UTC),
        series_id=series_id,
        group_id=group_id,
    )


def _decided_topic() -> Topic:
    return Topic(
        id="t1",
        name="価格",
        decision_criteria="¥価格 確定",
        time_budget_pct=20,
        priority=TopicPriority.CRITICAL,
        state=TopicState.DECIDED,
        evidence_quote="では¥1200で進めます",
    )


def _candidate() -> InterventionCandidate:
    return InterventionCandidate(
        meeting_id="m-current",
        agent="DecisionCapture",
        content="決定: ¥1200/月 (担当: 田中, 期日: 2026-06-30)",
        reason="decision_captured",
        evidence_quote="では¥1200で",
        confidence=0.85,
    )


@pytest.mark.asyncio
async def test_persist_decision_creates_with_deterministic_id(
    monkeypatch: pytest.MonkeyPatch,
):
    """meeting + topic id から ID が deterministic に組まれ、upsert に渡る。"""
    from helmsman.services import decision_persistence as mod

    captured: dict = {}

    async def fake_embed(texts: list[str]):
        return [[0.1, 0.2, 0.3]], None

    monkeypatch.setattr(mod, "embed_texts", fake_embed)
    monkeypatch.setattr(mod, "upsert_decision", AsyncMock(return_value=True))

    fake_repo = AsyncMock()
    async def fake_upsert(d):
        captured["decision"] = d
        return d

    fake_repo.upsert = fake_upsert

    result = await mod.persist_decision(
        meeting=_meeting(),
        topic=_decided_topic(),
        candidate=_candidate(),
        repo=fake_repo,
    )
    assert result is not None
    assert captured["decision"].id == "m-current:t1"
    assert captured["decision"].topic_name == "価格"
    # evidence_quote が decision_text に流れる (topic.evidence_quote 優先)
    assert "¥1200" in captured["decision"].decision_text
    assert captured["decision"].embedding == [0.1, 0.2, 0.3]


@pytest.mark.asyncio
async def test_persist_decision_inherits_series_and_group(
    monkeypatch: pytest.MonkeyPatch,
):
    """meeting の series_id / group_id が Decision にコピーされる。"""
    from helmsman.services import decision_persistence as mod

    captured: dict = {}

    async def fake_embed(texts: list[str]):
        return [[0.0]], None

    monkeypatch.setattr(mod, "embed_texts", fake_embed)
    monkeypatch.setattr(mod, "upsert_decision", AsyncMock(return_value=False))

    fake_repo = AsyncMock()
    async def fake_upsert(d):
        captured["decision"] = d
        return d
    fake_repo.upsert = fake_upsert

    await mod.persist_decision(
        meeting=_meeting(series_id="s-weekly", group_id="g-launch"),
        topic=_decided_topic(),
        candidate=_candidate(),
        repo=fake_repo,
    )
    assert captured["decision"].series_id == "s-weekly"
    assert captured["decision"].group_id == "g-launch"


@pytest.mark.asyncio
async def test_persist_decision_applies_embed_usage_to_sink(
    monkeypatch: pytest.MonkeyPatch,
):
    """embed の usage が sink に積み上がる (コスト追跡)。"""
    from helmsman.services import decision_persistence as mod

    sink = MeetingUsage()
    usage = UsageRecord(
        agent_name="EmbeddingService",
        model_deployment="text-embedding-3-small",
        prompt_tokens=20,
        completion_tokens=0,
        total_tokens=20,
    )

    async def fake_embed(texts: list[str]):
        return [[0.0]], usage

    monkeypatch.setattr(mod, "embed_texts", fake_embed)
    monkeypatch.setattr(mod, "upsert_decision", AsyncMock(return_value=False))

    fake_repo = AsyncMock()
    fake_repo.upsert = AsyncMock(side_effect=lambda d: d)

    await mod.persist_decision(
        meeting=_meeting(),
        topic=_decided_topic(),
        candidate=_candidate(),
        usage_sink=sink,
        repo=fake_repo,
    )
    assert sink.total_tokens == 20


@pytest.mark.asyncio
async def test_persist_decision_survives_embed_failure(
    monkeypatch: pytest.MonkeyPatch,
):
    """embed が落ちても Cosmos 保存は続行 (embedding=None で書く)。"""
    from helmsman.services import decision_persistence as mod

    async def boom(texts: list[str]):
        raise RuntimeError("embed boom")

    monkeypatch.setattr(mod, "embed_texts", boom)
    monkeypatch.setattr(mod, "upsert_decision", AsyncMock(return_value=False))

    fake_repo = AsyncMock()
    captured: dict = {}
    async def fake_upsert(d):
        captured["decision"] = d
        return d
    fake_repo.upsert = fake_upsert

    result = await mod.persist_decision(
        meeting=_meeting(),
        topic=_decided_topic(),
        candidate=_candidate(),
        repo=fake_repo,
    )
    assert result is not None
    assert captured["decision"].embedding is None


@pytest.mark.asyncio
async def test_persist_decision_returns_none_on_cosmos_failure(
    monkeypatch: pytest.MonkeyPatch,
):
    """Cosmos upsert が落ちたら None を返す (致命にしない)。"""
    from helmsman.services import decision_persistence as mod

    async def fake_embed(texts: list[str]):
        return [[0.0]], None

    monkeypatch.setattr(mod, "embed_texts", fake_embed)

    fake_repo = AsyncMock()
    fake_repo.upsert = AsyncMock(side_effect=RuntimeError("cosmos boom"))
    search_spy = AsyncMock(return_value=False)
    monkeypatch.setattr(mod, "upsert_decision", search_spy)

    result = await mod.persist_decision(
        meeting=_meeting(),
        topic=_decided_topic(),
        candidate=_candidate(),
        repo=fake_repo,
    )
    assert result is None
    # search はそもそも呼ばれない (Cosmos が先に失敗してるので)
    search_spy.assert_not_called()


@pytest.mark.asyncio
async def test_persist_decision_continues_when_search_fails(
    monkeypatch: pytest.MonkeyPatch,
):
    """AI Search upsert が落ちても decision は返す (Cosmos 側は OK なので)。"""
    from helmsman.services import decision_persistence as mod

    async def fake_embed(texts: list[str]):
        return [[0.0]], None

    monkeypatch.setattr(mod, "embed_texts", fake_embed)
    monkeypatch.setattr(
        mod, "upsert_decision", AsyncMock(side_effect=RuntimeError("search boom"))
    )

    fake_repo = AsyncMock()
    fake_repo.upsert = AsyncMock(side_effect=lambda d: d)

    result = await mod.persist_decision(
        meeting=_meeting(),
        topic=_decided_topic(),
        candidate=_candidate(),
        repo=fake_repo,
    )
    assert result is not None  # Cosmos には書けてる
