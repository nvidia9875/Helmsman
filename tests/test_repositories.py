"""Cosmos repository async-mock tests.

Cosmos の async client (`azure.cosmos.aio.ContainerProxy`) を AsyncMock で
差し替えて、Repository が期待通りの partition_key / クエリパラメータを
渡しているかを検証する。実際の Cosmos には繋がない。
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from helmsman.models.document import Document
from helmsman.models.meeting import Meeting, MeetingMode, MeetingState


def _meeting(
    *,
    meeting_id: str = "m-1",
    organizer_id: str = "u-1",
    goal: str = "g",
    series_id: str | None = None,
    series_index: int | None = None,
) -> Meeting:
    return Meeting(
        id=meeting_id,
        organizer_id=organizer_id,
        goal=goal,
        mode=MeetingMode.DECISION,
        state=MeetingState.IN_PROGRESS,
        started_at=datetime.now(UTC),
        series_id=series_id,
        series_index=series_index,
    )


def _async_iter(items: list[dict[str, Any]]):
    """list[dict] を async iterator として返す helper。"""

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


def _make_container_mock(query_results: list[dict[str, Any]] | None = None) -> MagicMock:
    """ContainerProxy の最低限の async インタフェース mock。"""
    container = MagicMock()
    container.create_item = AsyncMock()
    container.upsert_item = AsyncMock()
    container.read_item = AsyncMock()
    container.query_items = MagicMock(return_value=_async_iter(query_results or []))
    return container


# ===== MeetingRepository =====


@pytest.mark.asyncio
async def test_meeting_repo_create_dumps_json(monkeypatch: pytest.MonkeyPatch) -> None:
    from helmsman.repositories.meetings import MeetingRepository

    container = _make_container_mock()
    repo = MeetingRepository()
    monkeypatch.setattr(repo, "_get_container", AsyncMock(return_value=container))

    m = _meeting()
    result = await repo.create(m)

    assert result is m
    container.create_item.assert_awaited_once()
    call = container.create_item.await_args
    body = call.kwargs.get("body") or call.args[0]
    assert body["id"] == "m-1"
    assert body["organizer_id"] == "u-1"


@pytest.mark.asyncio
async def test_meeting_repo_get_passes_partition_key(monkeypatch: pytest.MonkeyPatch) -> None:
    from helmsman.repositories.meetings import MeetingRepository

    container = _make_container_mock()
    container.read_item = AsyncMock(return_value=_meeting().model_dump(mode="json"))
    repo = MeetingRepository()
    monkeypatch.setattr(repo, "_get_container", AsyncMock(return_value=container))

    m = await repo.get("m-1", "u-1")
    assert m is not None and m.id == "m-1"
    container.read_item.assert_awaited_once_with(item="m-1", partition_key="u-1")


@pytest.mark.asyncio
async def test_meeting_repo_get_returns_none_on_not_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from azure.cosmos.exceptions import CosmosResourceNotFoundError

    from helmsman.repositories.meetings import MeetingRepository

    container = _make_container_mock()
    container.read_item = AsyncMock(
        side_effect=CosmosResourceNotFoundError(message="404", response=None)
    )
    repo = MeetingRepository()
    monkeypatch.setattr(repo, "_get_container", AsyncMock(return_value=container))

    assert await repo.get("missing", "u-1") is None


@pytest.mark.asyncio
async def test_meeting_repo_list_by_organizer_uses_partition_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from helmsman.repositories.meetings import MeetingRepository

    rows = [
        _meeting(meeting_id="m-1").model_dump(mode="json"),
        _meeting(meeting_id="m-2").model_dump(mode="json"),
    ]
    container = _make_container_mock(query_results=rows)
    repo = MeetingRepository()
    monkeypatch.setattr(repo, "_get_container", AsyncMock(return_value=container))

    out = await repo.list_by_organizer("u-1", limit=5)
    assert [m.id for m in out] == ["m-1", "m-2"]

    args = container.query_items.call_args.kwargs
    assert args["partition_key"] == "u-1"
    assert any(p["name"] == "@oid" and p["value"] == "u-1" for p in args["parameters"])
    assert any(p["name"] == "@lim" and p["value"] == 5 for p in args["parameters"])


@pytest.mark.asyncio
async def test_meeting_repo_list_series_filters_by_series_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from helmsman.repositories.meetings import MeetingRepository

    rows = [
        _meeting(meeting_id="m-1", series_id="s-1", series_index=1).model_dump(mode="json"),
        _meeting(meeting_id="m-2", series_id="s-1", series_index=2).model_dump(mode="json"),
    ]
    container = _make_container_mock(query_results=rows)
    repo = MeetingRepository()
    monkeypatch.setattr(repo, "_get_container", AsyncMock(return_value=container))

    out = await repo.list_series("s-1", "u-1")
    assert [m.series_index for m in out] == [1, 2]

    args = container.query_items.call_args.kwargs
    assert args["partition_key"] == "u-1"
    assert any(p["name"] == "@sid" and p["value"] == "s-1" for p in args["parameters"])


# ===== DocumentRepository =====


def _document(*, document_id: str = "d-1", meeting_id: str = "m-1") -> Document:
    return Document(
        id=document_id,
        meeting_id=meeting_id,
        filename="spec.pdf",
        mime_type="application/pdf",
        size_bytes=1024,
        blob_path=f"{meeting_id}/{document_id}/spec.pdf",
        uploaded_by="u-1",
    )


@pytest.mark.asyncio
async def test_document_repo_list_by_meeting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from helmsman.repositories.documents import DocumentRepository

    rows = [
        _document(document_id="d-1").model_dump(mode="json"),
        _document(document_id="d-2").model_dump(mode="json"),
    ]
    container = _make_container_mock(query_results=rows)
    repo = DocumentRepository()
    monkeypatch.setattr(repo, "_get_container", AsyncMock(return_value=container))

    out = await repo.list_by_meeting("m-1")
    assert [d.id for d in out] == ["d-1", "d-2"]

    args = container.query_items.call_args.kwargs
    assert args["partition_key"] == "m-1"
    assert any(p["name"] == "@mid" and p["value"] == "m-1" for p in args["parameters"])


@pytest.mark.asyncio
async def test_document_repo_get_returns_none_on_not_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from azure.cosmos.exceptions import CosmosResourceNotFoundError

    from helmsman.repositories.documents import DocumentRepository

    container = _make_container_mock()
    container.read_item = AsyncMock(
        side_effect=CosmosResourceNotFoundError(message="404", response=None)
    )
    repo = DocumentRepository()
    monkeypatch.setattr(repo, "_get_container", AsyncMock(return_value=container))

    assert await repo.get("missing", "m-1") is None
