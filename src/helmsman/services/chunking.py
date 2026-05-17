"""Naive sliding-window text chunker for RAG ingestion.

文字数ベースで分割。トークンベースが理想だが、ハッカソンの精度には十分。
"""
from __future__ import annotations


def chunk_text(
    text: str, *, chunk_size: int = 1200, overlap: int = 200
) -> list[str]:
    """テキストをスライディングウィンドウで分割。

    chunk_size 文字、overlap 文字重複。空文字や空白だけのチャンクは除外。
    """
    if not text:
        return []
    if chunk_size <= overlap:
        raise ValueError("chunk_size must exceed overlap")

    chunks: list[str] = []
    step = chunk_size - overlap
    pos = 0
    while pos < len(text):
        piece = text[pos : pos + chunk_size].strip()
        if piece:
            chunks.append(piece)
        pos += step
    return chunks
