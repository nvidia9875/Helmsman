"""RAG smoke 検証 — 本番 Azure AI Search で embed → upsert → vector search が動くか確認。

Usage:
  AZURE_SEARCH_ENDPOINT=https://helmsman-dev-search-zzfj7ngjdvn3s.search.windows.net \
  AZURE_SEARCH_KEY=$(az search admin-key show -g rg-helmsman-dev \
      --service-name helmsman-dev-search-zzfj7ngjdvn3s --query primaryKey -o tsv) \
  uv run python scripts/smoke_rag.py

実行内容:
  1. ensure_index() で HNSW index 作成 (idempotent)
  2. fixture テキスト → chunk → embed → upsert
  3. ベクトル検索で goal クエリへの hit 確認
  4. recall@k と latency を表示
  5. (オプション) 最後にテスト index を消す
"""
from __future__ import annotations

import asyncio
import os
import time
import uuid
from pathlib import Path

from helmsman.models.document import DocumentChunk
from helmsman.services.chunking import chunk_text
from helmsman.services.embeddings import embed_texts
from helmsman.services.search_index import (
    ensure_index,
    search_meeting_chunks,
    upsert_chunks,
)

# 試験文書 (YouTube マーケ戦略 Memo の合成版)
TEST_DOC = """
# YouTube Channel Strategy Memo (Q3 2026)

## 3H コンテンツ戦略 (Hero / Hub / Help)
- Hero: 月 2 本、ブランド認知重視。トーンは編集された動画ジャーナリズム。
- Hub: 週 1 本、登録者の継続視聴維持。シリーズ化されたケーススタディ。
- Help: 必要に応じて週 2-3 本、検索流入を狙う how-to 動画。

## 制作リソース
- 編集者は外部委託、月 30 本までスケール可能。
- 撮影は社内スタジオ + 月 1 回の外ロケ。
- 投資配分: Hero 50% / Hub 30% / Help 20%。

## 視覚デザイン
- サムネは青字に黄字テンプレで統一。
- ロゴは右上、視聴者の目線移動を妨げない。

## 商談導線
- Hero 動画の最終フレームに資料 DL CTA。
- Hub の概要欄に商談予約フォーム。
- Help は SEO 最大化のためタイトル + チャプター重視。

## KPI と継続観察
- 主目標: 商談予約数 (月次)。
- 副目標: 平均視聴時間 + 登録者増分。
- 「再生回数を主目標に」とは扱わない。
"""

TEST_MEETING_ID = f"smoke-{uuid.uuid4().hex[:8]}"
TEST_DOC_ID = f"doc-{uuid.uuid4().hex[:8]}"

# 検索クエリ (goal を模した自然文)
TEST_QUERIES = [
    "YouTube チャンネル運営方針を決定する",
    "KPI と評価指標は何にすべきか",
    "Hero と Hub の投資配分",
]


async def main() -> int:
    if not os.getenv("AZURE_SEARCH_ENDPOINT") or not os.getenv("AZURE_SEARCH_KEY"):
        print("ERROR: AZURE_SEARCH_ENDPOINT / AZURE_SEARCH_KEY が未設定")
        return 1

    print(f"=== Helmsman RAG smoke: meeting={TEST_MEETING_ID} doc={TEST_DOC_ID} ===\n")

    # 1. index 作成
    t0 = time.perf_counter()
    await ensure_index()
    print(f"[1] ensure_index: {(time.perf_counter() - t0) * 1000:.0f} ms")

    # 2. chunk + embed
    chunks_text = chunk_text(TEST_DOC)
    print(f"[2] chunked: {len(chunks_text)} pieces")

    t0 = time.perf_counter()
    vectors, usage = await embed_texts(chunks_text)
    embed_ms = (time.perf_counter() - t0) * 1000
    print(
        f"[3] embedded: {len(vectors)} vectors (dim={len(vectors[0]) if vectors else 0}) "
        f"in {embed_ms:.0f} ms, prompt_tokens={usage.prompt_tokens if usage else 0}"
    )

    # 3. upsert
    chunks = [
        DocumentChunk(
            document_id=TEST_DOC_ID,
            meeting_id=TEST_MEETING_ID,
            group_id=None,
            chunk_index=i,
            text=t,
            embedding=v,
        )
        for i, (t, v) in enumerate(zip(chunks_text, vectors, strict=True))
    ]
    t0 = time.perf_counter()
    upserted = await upsert_chunks(chunks)
    upsert_ms = (time.perf_counter() - t0) * 1000
    print(f"[4] upserted: {upserted}/{len(chunks)} chunks in {upsert_ms:.0f} ms")

    # index がコミットされるのを待つ (Azure Search は eventual consistency)
    await asyncio.sleep(2.0)

    # 4. vector search
    print("\n=== Vector search results ===")
    for q in TEST_QUERIES:
        t0 = time.perf_counter()
        qvecs, _ = await embed_texts([q])
        embed_q_ms = (time.perf_counter() - t0) * 1000

        t0 = time.perf_counter()
        hits = await search_meeting_chunks(
            meeting_id=TEST_MEETING_ID,
            query_embedding=qvecs[0],
            top_k=3,
        )
        search_ms = (time.perf_counter() - t0) * 1000

        print(f"\nquery: {q}")
        print(
            f"  embed: {embed_q_ms:.0f} ms / search: {search_ms:.0f} ms / hits: {len(hits)}"
        )
        for i, h in enumerate(hits, 1):
            snippet = h.get("text", "").strip().split("\n")[0][:60]
            score = h.get("@search.score", 0.0)
            print(f"  [{i}] score={score:.3f}  {snippet}")

    # 5. cleanup option
    print(
        f"\n=== Cleanup ===\n"
        f"Test chunks remain in index for inspection. To remove:\n"
        f"  curl -X POST -H 'api-key: $AZURE_SEARCH_KEY' \\\n"
        f"    'https://helmsman-dev-search-zzfj7ngjdvn3s.search.windows.net"
        f"/indexes/helmsman-documents/docs/index?api-version=2024-07-01' \\\n"
        f"    -d '{{\"value\":[{{\"@search.action\":\"delete\",\"id\":\"<chunk_id>\"}}]}}'"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
