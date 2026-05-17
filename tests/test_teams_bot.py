"""Tests for the Teams bot operation_context parser."""
from __future__ import annotations

from helmsman.services.teams_bot import (
    _build_operation_context,
    parse_operation_context,
)


def test_build_and_parse_roundtrip() -> None:
    ctx = _build_operation_context("meet-123", "u-456")
    meeting_id, organizer_id = parse_operation_context(ctx)
    assert meeting_id == "meet-123"
    assert organizer_id == "u-456"


def test_parse_empty_returns_none_tuple() -> None:
    assert parse_operation_context("") == (None, None)
    assert parse_operation_context(None) == (None, None)


def test_parse_malformed_returns_partial() -> None:
    # missing org: part
    meeting_id, organizer_id = parse_operation_context("meeting:abc")
    assert meeting_id == "abc"
    assert organizer_id is None


def test_parse_ignores_unknown_segments() -> None:
    ctx = "meeting:m1|org:u1|extra:foo"
    meeting_id, organizer_id = parse_operation_context(ctx)
    assert meeting_id == "m1"
    assert organizer_id == "u1"
