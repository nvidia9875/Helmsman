"""Chunking unit tests."""
from __future__ import annotations

import pytest

from helmsman.services.chunking import chunk_text


def test_chunk_empty_returns_empty_list() -> None:
    assert chunk_text("") == []


def test_chunk_smaller_than_window_returns_single_piece() -> None:
    text = "短いテキスト"
    chunks = chunk_text(text, chunk_size=100, overlap=10)
    assert chunks == [text]


def test_chunk_overlap_respects_step() -> None:
    text = "a" * 250
    chunks = chunk_text(text, chunk_size=100, overlap=20)
    # step = 80, so chunks start at 0, 80, 160, 240
    assert len(chunks) == 4
    assert all(len(c) <= 100 for c in chunks)


def test_chunk_rejects_overlap_ge_size() -> None:
    with pytest.raises(ValueError):
        chunk_text("xxx", chunk_size=10, overlap=10)


def test_chunk_skips_whitespace_only_pieces() -> None:
    # 100 文字の空白だけ → 1 つも追加されない
    text = " " * 100
    chunks = chunk_text(text, chunk_size=50, overlap=10)
    assert chunks == []
