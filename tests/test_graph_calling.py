"""Tests for graph_calling.py (operation_context parser + token cache helpers)."""
from __future__ import annotations

import pytest

from helmsman.services.graph_calling import (
    _build_operation_context,
    _TokenCache,
    is_configured,
    parse_operation_context,
)


def test_build_and_parse_roundtrip() -> None:
    ctx = _build_operation_context("m-abc", "u-xyz")
    meeting_id, organizer_id = parse_operation_context(ctx)
    assert meeting_id == "m-abc"
    assert organizer_id == "u-xyz"


def test_parse_empty_and_none() -> None:
    assert parse_operation_context("") == (None, None)
    assert parse_operation_context(None) == (None, None)


def test_parse_partial() -> None:
    meeting_id, organizer_id = parse_operation_context("meeting:only")
    assert meeting_id == "only"
    assert organizer_id is None


def test_parse_ignores_unknown_segments() -> None:
    ctx = "meeting:m1|org:u1|extra:foo|noise"
    meeting_id, organizer_id = parse_operation_context(ctx)
    assert meeting_id == "m1"
    assert organizer_id == "u1"


def test_is_configured_returns_bool() -> None:
    # 環境依存だが少なくとも bool が返ることを保証
    result = is_configured()
    assert isinstance(result, bool)


def test_token_cache_dataclass() -> None:
    cache = _TokenCache()
    assert cache.token is None
    assert cache.expires_at == 0.0
    cache.token = "abc"
    cache.expires_at = 9999.0
    assert cache.token == "abc"


@pytest.mark.asyncio
async def test_get_token_uses_cache_when_valid() -> None:
    """有効期限内ならキャッシュを返す。fetcher は呼ばれない。"""
    import time

    from helmsman.services.graph_calling import _get_token

    cache = _TokenCache(token="cached-tok", expires_at=time.time() + 3600)
    call_count = 0

    async def fetcher() -> tuple[str, int]:
        nonlocal call_count
        call_count += 1
        return ("new-tok", 3600)

    result = await _get_token(cache, fetcher)
    assert result == "cached-tok"
    assert call_count == 0


@pytest.mark.asyncio
async def test_get_token_fetches_when_expired() -> None:
    """期限切れまたは未取得なら fetcher を呼ぶ。"""
    from helmsman.services.graph_calling import _get_token

    cache = _TokenCache()  # token=None, expires_at=0
    call_count = 0

    async def fetcher() -> tuple[str, int]:
        nonlocal call_count
        call_count += 1
        return ("fresh-tok", 3600)

    result = await _get_token(cache, fetcher)
    assert result == "fresh-tok"
    assert call_count == 1
    # 二度目はキャッシュから返る
    result2 = await _get_token(cache, fetcher)
    assert result2 == "fresh-tok"
    assert call_count == 1
