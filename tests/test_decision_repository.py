"""DecisionRepository — Cosmos mock を使った partition_key + query 検証。

実 Cosmos には接続せず、ContainerProxy を AsyncMock で差し替える。
list_by_organizer の within_days フィルタや list_by_series の partition 利用が
意図通りかを検査する。
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from helmsman.models.decision import Decision


def _decision(
    *,
    decision_id: str = "m1:t1",
    organizer_id: str = "u-1",
    meeting_id: str = "m1",
    topic_id: str = "t1",
    series_id: str | None = None,
    group_id: str | None = None,
) -> Decision:
    return Decision(
        id=decision_id,
        organizer_id=organizer_id,
        meeting_id=meeting_id,
        topic_id=topic_id,
        topic_name="価格",
        decision_text="¥1200/月で進める",
        owner="田中",
        deadline="2026-06-30",
        evidence_quote="では1200で",
        series_id=series_id,
        group_id=group_id,
        confidence=0.85,
        captured_at=datetime.now(UTC),
    )


def _async_iter(items: list[dict[str, Any]]):
    class _Iter:
        def __init__(self, src: list[dict[str, Any]]) -> None:
            self._src = iter(src)

        def __aiter__(self):
            return self

        async def __anext__(self) -> dict[str, Any]:
            try:
                return next(self._src)
            except StopIteration:
                raise StopAsyncIteration from None

    return _Iter(items)


def _container_mock(rows: list[dict[str, Any]] | None = None) -> MagicMock:
    c = MagicMock()
    c.upsert_item = AsyncMock()
    c.read_item = AsyncMock()
    c.delete_item = AsyncMock()
    c.query_items = MagicMock(return_value=_async_iter(rows or []))
    return c


@pytest.mark.asyncio
async def test_upsert_uses_model_dump_json_and_touches_updated_at(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from helmsman.repositories.decisions import DecisionRepository

    container = _container_mock()
    repo = DecisionRepository()
    monkeypatch.setattr(repo, "_get_container", AsyncMock(return_value=container))

    d = _decision()
    before = d.updated_at
    out = await repo.upsert(d)

    assert out is d
    container.upsert_item.assert_awaited_once()
    body = container.upsert_item.call_args.kwargs["body"]
    assert body["id"] == "m1:t1"
    # touch されているはず (>= before、通常 > before)
    assert out.updated_at >= before


@pytest.mark.asyncio
async def test_get_passes_partition_key(monkeypatch: pytest.MonkeyPatch) -> None:
    from helmsman.repositories.decisions import DecisionRepository

    container = _container_mock()
    container.read_item = AsyncMock(return_value=_decision().model_dump(mode="json"))
    repo = DecisionRepository()
    monkeypatch.setattr(repo, "_get_container", AsyncMock(return_value=container))

    d = await repo.get("m1:t1", "u-1")
    assert d is not None and d.id == "m1:t1"
    container.read_item.assert_awaited_once_with(item="m1:t1", partition_key="u-1")


@pytest.mark.asyncio
async def test_get_returns_none_on_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    from azure.cosmos.exceptions import CosmosResourceNotFoundError

    from helmsman.repositories.decisions import DecisionRepository

    container = _container_mock()
    container.read_item = AsyncMock(
        side_effect=CosmosResourceNotFoundError(message="404", response=None)
    )
    repo = DecisionRepository()
    monkeypatch.setattr(repo, "_get_container", AsyncMock(return_value=container))

    assert await repo.get("missing", "u-1") is None


@pytest.mark.asyncio
async def test_list_by_organizer_applies_within_days_filter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from helmsman.repositories.decisions import DecisionRepository

    rows = [_decision(decision_id="m1:t1").model_dump(mode="json")]
    container = _container_mock(rows)
    repo = DecisionRepository()
    monkeypatch.setattr(repo, "_get_container", AsyncMock(return_value=container))

    out = await repo.list_by_organizer("u-1", within_days=30, limit=10)
    assert [d.id for d in out] == ["m1:t1"]

    args = container.query_items.call_args.kwargs
    assert args["partition_key"] == "u-1"
    # within_days を指定 → @cutoff パラメータが入る
    assert any(p["name"] == "@cutoff" for p in args["parameters"])
    assert "c.captured_at >= @cutoff" in args["query"]


@pytest.mark.asyncio
async def test_list_by_organizer_without_window_omits_cutoff(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from helmsman.repositories.decisions import DecisionRepository

    container = _container_mock([])
    repo = DecisionRepository()
    monkeypatch.setattr(repo, "_get_container", AsyncMock(return_value=container))

    await repo.list_by_organizer("u-1", within_days=None)

    args = container.query_items.call_args.kwargs
    assert all(p["name"] != "@cutoff" for p in args["parameters"])
    assert "@cutoff" not in args["query"]


@pytest.mark.asyncio
async def test_list_by_series_filters_by_series_id_and_organizer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from helmsman.repositories.decisions import DecisionRepository

    rows = [
        _decision(decision_id="m1:t1", series_id="s-1").model_dump(mode="json"),
        _decision(decision_id="m2:t1", meeting_id="m2", series_id="s-1").model_dump(mode="json"),
    ]
    container = _container_mock(rows)
    repo = DecisionRepository()
    monkeypatch.setattr(repo, "_get_container", AsyncMock(return_value=container))

    out = await repo.list_by_series("s-1", "u-1")
    assert [d.id for d in out] == ["m1:t1", "m2:t1"]

    args = container.query_items.call_args.kwargs
    assert args["partition_key"] == "u-1"
    assert any(p["name"] == "@sid" and p["value"] == "s-1" for p in args["parameters"])
    assert any(p["name"] == "@oid" and p["value"] == "u-1" for p in args["parameters"])


@pytest.mark.asyncio
async def test_list_by_group_filters_by_group_id(monkeypatch: pytest.MonkeyPatch) -> None:
    from helmsman.repositories.decisions import DecisionRepository

    rows = [_decision(decision_id="m1:t1", group_id="g-1").model_dump(mode="json")]
    container = _container_mock(rows)
    repo = DecisionRepository()
    monkeypatch.setattr(repo, "_get_container", AsyncMock(return_value=container))

    out = await repo.list_by_group("g-1", "u-1")
    assert len(out) == 1

    args = container.query_items.call_args.kwargs
    assert any(p["name"] == "@gid" and p["value"] == "g-1" for p in args["parameters"])


@pytest.mark.asyncio
async def test_list_by_meeting_filters_by_meeting_id(monkeypatch: pytest.MonkeyPatch) -> None:
    from helmsman.repositories.decisions import DecisionRepository

    rows = [
        _decision(decision_id="m1:t1").model_dump(mode="json"),
        _decision(decision_id="m1:t2", topic_id="t2").model_dump(mode="json"),
    ]
    container = _container_mock(rows)
    repo = DecisionRepository()
    monkeypatch.setattr(repo, "_get_container", AsyncMock(return_value=container))

    out = await repo.list_by_meeting("m1", "u-1")
    assert [d.id for d in out] == ["m1:t1", "m1:t2"]

    args = container.query_items.call_args.kwargs
    assert any(p["name"] == "@mid" and p["value"] == "m1" for p in args["parameters"])


@pytest.mark.asyncio
async def test_delete_returns_true_on_success(monkeypatch: pytest.MonkeyPatch) -> None:
    from helmsman.repositories.decisions import DecisionRepository

    container = _container_mock()
    repo = DecisionRepository()
    monkeypatch.setattr(repo, "_get_container", AsyncMock(return_value=container))

    assert await repo.delete("m1:t1", "u-1") is True
    container.delete_item.assert_awaited_once_with(item="m1:t1", partition_key="u-1")


@pytest.mark.asyncio
async def test_delete_returns_false_on_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    from azure.cosmos.exceptions import CosmosResourceNotFoundError

    from helmsman.repositories.decisions import DecisionRepository

    container = _container_mock()
    container.delete_item = AsyncMock(
        side_effect=CosmosResourceNotFoundError(message="404", response=None)
    )
    repo = DecisionRepository()
    monkeypatch.setattr(repo, "_get_container", AsyncMock(return_value=container))

    assert await repo.delete("missing", "u-1") is False
