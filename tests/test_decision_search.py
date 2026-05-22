"""decision_search — boost / cosine / フォールバック path の単体テスト。

AI Search 経路は azure-search-documents の async client を mock するのが重く、
ここでは _is_search_configured が False (デフォルト dev env) のフォールバック
path を中心に検証する。AI Search path のテストは別途 integration で行う。
"""
from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from helmsman.models.decision import Decision
from helmsman.services.decision_search import (
    BOOST_SAME_GROUP,
    BOOST_SAME_SERIES,
    DECAY_OVER_90_DAYS,
    _cosine,
    _index_name,
    apply_boost,
    search_decisions,
)


def _make(
    *,
    decision_id: str,
    organizer_id: str = "u-1",
    series_id: str | None = None,
    group_id: str | None = None,
    embedding: list[float] | None = None,
    captured_days_ago: float = 0,
) -> Decision:
    return Decision(
        id=decision_id,
        organizer_id=organizer_id,
        meeting_id=decision_id.split(":")[0],
        topic_id=decision_id.split(":")[1] if ":" in decision_id else "t",
        topic_name="価格",
        decision_text="¥1200/月で進める",
        owner="田中",
        series_id=series_id,
        group_id=group_id,
        embedding=embedding,
        captured_at=datetime.now(UTC) - timedelta(days=captured_days_ago),
    )


# ===== _cosine =====


def test_cosine_identical_vectors_is_one():
    assert math.isclose(_cosine([1.0, 0.0], [1.0, 0.0]), 1.0)


def test_cosine_orthogonal_is_zero():
    assert _cosine([1.0, 0.0], [0.0, 1.0]) == 0.0


def test_cosine_opposite_is_minus_one():
    assert math.isclose(_cosine([1.0, 0.0], [-1.0, 0.0]), -1.0)


def test_cosine_handles_empty_inputs():
    assert _cosine([], [1.0, 2.0]) == 0.0
    assert _cosine([1.0, 2.0], []) == 0.0


def test_cosine_handles_length_mismatch():
    assert _cosine([1.0, 2.0], [1.0, 2.0, 3.0]) == 0.0


def test_cosine_handles_zero_vector():
    assert _cosine([0.0, 0.0, 0.0], [1.0, 2.0, 3.0]) == 0.0


# ===== apply_boost =====


def test_boost_same_series_adds_constant():
    d = _make(decision_id="m1:t1", series_id="s-1")
    out = apply_boost(0.5, d, series_id="s-1", group_id=None)
    assert math.isclose(out, 0.5 + BOOST_SAME_SERIES, abs_tol=1e-6)


def test_boost_same_group_adds_constant():
    d = _make(decision_id="m1:t1", group_id="g-1")
    out = apply_boost(0.5, d, series_id=None, group_id="g-1")
    assert math.isclose(out, 0.5 + BOOST_SAME_GROUP, abs_tol=1e-6)


def test_boost_stacks_series_and_group():
    d = _make(decision_id="m1:t1", series_id="s-1", group_id="g-1")
    out = apply_boost(0.5, d, series_id="s-1", group_id="g-1")
    expected = 0.5 + BOOST_SAME_SERIES + BOOST_SAME_GROUP
    assert math.isclose(out, expected, abs_tol=1e-6)


def test_boost_mismatched_series_no_change():
    d = _make(decision_id="m1:t1", series_id="s-1")
    out = apply_boost(0.5, d, series_id="other", group_id=None)
    assert math.isclose(out, 0.5, abs_tol=1e-6)


def test_decay_full_after_90_days():
    d = _make(decision_id="m1:t1", captured_days_ago=90)
    out = apply_boost(1.0, d, series_id=None, group_id=None)
    assert math.isclose(out, 1.0 - DECAY_OVER_90_DAYS, abs_tol=1e-3)


def test_decay_half_after_45_days():
    d = _make(decision_id="m1:t1", captured_days_ago=45)
    out = apply_boost(1.0, d, series_id=None, group_id=None)
    expected = 1.0 - DECAY_OVER_90_DAYS / 2
    assert math.isclose(out, expected, abs_tol=1e-3)


def test_decay_caps_at_90_days_constant():
    """90日超でも追加で減衰しない (線形 cap)。"""
    d = _make(decision_id="m1:t1", captured_days_ago=180)
    out = apply_boost(1.0, d, series_id=None, group_id=None)
    assert math.isclose(out, 1.0 - DECAY_OVER_90_DAYS, abs_tol=1e-3)


# ===== _index_name =====


def test_index_name_appends_decisions_suffix(monkeypatch: pytest.MonkeyPatch):
    from helmsman.core.config import get_settings

    get_settings.cache_clear()
    monkeypatch.setenv("AZURE_SEARCH_INDEX_NAME", "helmsman-documents")
    try:
        assert _index_name() == "helmsman-decisions"
    finally:
        get_settings.cache_clear()


def test_index_name_already_decisions_kept_as_is(monkeypatch: pytest.MonkeyPatch):
    from helmsman.core.config import get_settings

    get_settings.cache_clear()
    monkeypatch.setenv("AZURE_SEARCH_INDEX_NAME", "my-decisions")
    try:
        assert _index_name() == "my-decisions"
    finally:
        get_settings.cache_clear()


def test_index_name_arbitrary_base(monkeypatch: pytest.MonkeyPatch):
    from helmsman.core.config import get_settings

    get_settings.cache_clear()
    monkeypatch.setenv("AZURE_SEARCH_INDEX_NAME", "rag")
    try:
        assert _index_name() == "rag-decisions"
    finally:
        get_settings.cache_clear()


# ===== search_decisions (fallback path) =====


@pytest.mark.asyncio
async def test_search_returns_empty_for_empty_embedding():
    out = await search_decisions(query_embedding=[], organizer_id="u-1")
    assert out == []


@pytest.mark.asyncio
async def test_fallback_ranks_by_cosine_similarity():
    """AI Search 未設定 → numpy/Cosmos フォールバックが cosine 順で返す。"""
    # 1.0,0.0 を query にして、似ているほど上位
    decisions = [
        _make(decision_id="m1:t1", embedding=[0.1, 0.99]),   # 違う方向 → 低
        _make(decision_id="m1:t2", embedding=[0.99, 0.1]),   # 似てる → 高
        _make(decision_id="m1:t3", embedding=[0.5, 0.5]),    # 中間
    ]
    repo = AsyncMock()
    repo.list_by_organizer = AsyncMock(return_value=decisions)

    out = await search_decisions(
        query_embedding=[1.0, 0.0],
        organizer_id="u-1",
        top_k=3,
        repo=repo,
    )
    assert [h.decision.id for h in out] == ["m1:t2", "m1:t3", "m1:t1"]
    repo.list_by_organizer.assert_awaited_once()


@pytest.mark.asyncio
async def test_fallback_skips_decisions_without_embedding():
    """embedding が無い decision は除外される。"""
    decisions = [
        _make(decision_id="m1:t1", embedding=[1.0, 0.0]),
        _make(decision_id="m1:t2", embedding=None),  # スキップ
        _make(decision_id="m1:t3", embedding=[0.9, 0.1]),
    ]
    repo = AsyncMock()
    repo.list_by_organizer = AsyncMock(return_value=decisions)

    out = await search_decisions(
        query_embedding=[1.0, 0.0],
        organizer_id="u-1",
        top_k=5,
        repo=repo,
    )
    assert [h.decision.id for h in out] == ["m1:t1", "m1:t3"]


@pytest.mark.asyncio
async def test_fallback_applies_series_boost_to_reorder():
    """同 series 一致でブーストすると順位が入れ替わる。"""
    decisions = [
        _make(decision_id="m1:t1", embedding=[0.8, 0.2], series_id=None),
        _make(decision_id="m1:t2", embedding=[0.7, 0.3], series_id="s-1"),  # boost
    ]
    repo = AsyncMock()
    repo.list_by_organizer = AsyncMock(return_value=decisions)

    # t1 のほうが cosine 高 (0.97 vs 0.92)、t2 に series boost +0.3 で逆転
    out = await search_decisions(
        query_embedding=[1.0, 0.0],
        organizer_id="u-1",
        series_id="s-1",
        top_k=2,
        repo=repo,
    )
    assert [h.decision.id for h in out] == ["m1:t2", "m1:t1"]


@pytest.mark.asyncio
async def test_fallback_respects_top_k():
    decisions = [
        _make(decision_id=f"m1:t{i}", embedding=[1.0 - i * 0.1, i * 0.1])
        for i in range(5)
    ]
    repo = AsyncMock()
    repo.list_by_organizer = AsyncMock(return_value=decisions)

    out = await search_decisions(
        query_embedding=[1.0, 0.0],
        organizer_id="u-1",
        top_k=2,
        repo=repo,
    )
    assert len(out) == 2


@pytest.mark.asyncio
async def test_fallback_passes_within_days_to_repo():
    repo = AsyncMock()
    repo.list_by_organizer = AsyncMock(return_value=[])

    await search_decisions(
        query_embedding=[1.0, 0.0],
        organizer_id="u-1",
        within_days=30,
        top_k=5,
        repo=repo,
    )
    call_kwargs = repo.list_by_organizer.call_args.kwargs
    assert call_kwargs["within_days"] == 30
