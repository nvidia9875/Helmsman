"""Decision (会議横断記憶) のベクトル検索サービス。

二段構成 (ADR-104):
  1. Azure AI Search が設定済 → HNSW vector index で類似検索
  2. 未設定 → Cosmos の Decision を全件取得 → in-process cosine で計算

スコアブースト:
  - 同 series_id ヒット: +0.30
  - 同 group_id ヒット: +0.15
  - captured_at が古いほど線形減衰 (90日で -0.20)

検索結果 (DecisionHit) は ``decision`` + 最終 ``score`` を持ち、
MemoryRetriever はこれを top_k 件 LLM に渡して relevance 判定する。
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime

from helmsman.core.config import get_settings
from helmsman.core.logging import logger
from helmsman.models.decision import Decision
from helmsman.repositories.decisions import DecisionRepository

VECTOR_DIM = 1536  # text-embedding-3-small
VECTOR_FIELD = "embedding"
DEFAULT_INDEX_NAME = "helmsman-decisions"

# スコアブーストの定数 (ADR-103)
BOOST_SAME_SERIES = 0.30
BOOST_SAME_GROUP = 0.15
DECAY_OVER_90_DAYS = 0.20


@dataclass
class DecisionHit:
    """検索結果 1 件 — Decision 本体 + 最終スコア (boost 後)。"""

    decision: Decision
    score: float


def _is_search_configured() -> bool:
    s = get_settings()
    return bool(s.azure_search_endpoint and s.azure_search_key)


def _index_name() -> str:
    """Decision 用 index 名 — document index と分離する。

    既存 search_index_name は document chunk 用に予約済。ここでは
    `{base}-decisions` の規約で別 index を切る。base が既に `-decisions` を
    含む場合はそのまま使う。
    """
    s = get_settings()
    base = s.azure_search_index_name or DEFAULT_INDEX_NAME
    if base.endswith("-decisions"):
        return base
    # `helmsman-documents` → `helmsman-decisions`
    if base.endswith("-documents"):
        return base[: -len("-documents")] + "-decisions"
    return f"{base}-decisions"


def _cosine(a: list[float], b: list[float]) -> float:
    """純 Python の cosine similarity。numpy 依存を避ける。

    長さ不一致 or どちらか空なら 0.0。
    """
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def apply_boost(
    base_score: float,
    decision: Decision,
    *,
    series_id: str | None,
    group_id: str | None,
    now: datetime | None = None,
) -> float:
    """スコアブースト/減衰を一元化 — Search/numpy 両 path から呼ぶ。"""
    score = base_score
    if series_id and decision.series_id == series_id:
        score += BOOST_SAME_SERIES
    if group_id and decision.group_id == group_id:
        score += BOOST_SAME_GROUP
    # 経過日数による線形減衰 (90日で DECAY_OVER_90_DAYS 引く)
    ref = now or datetime.now(UTC)
    delta = ref - decision.captured_at
    days = max(0.0, delta.total_seconds() / 86400.0)
    decay = min(DECAY_OVER_90_DAYS, days * (DECAY_OVER_90_DAYS / 90.0))
    return score - decay


# ===== Azure AI Search path =====


async def ensure_decision_index() -> None:
    """index が無ければ作る (idempotent)。Search 未設定なら no-op。"""
    if not _is_search_configured():
        return
    s = get_settings()
    from azure.core.credentials import AzureKeyCredential
    from azure.search.documents.indexes.aio import SearchIndexClient
    from azure.search.documents.indexes.models import (
        HnswAlgorithmConfiguration,
        SearchableField,
        SearchField,
        SearchFieldDataType,
        SearchIndex,
        SimpleField,
        VectorSearch,
        VectorSearchProfile,
    )

    fields = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True),
        SimpleField(
            name="organizer_id", type=SearchFieldDataType.String, filterable=True
        ),
        SimpleField(
            name="meeting_id", type=SearchFieldDataType.String, filterable=True
        ),
        SimpleField(
            name="topic_id", type=SearchFieldDataType.String, filterable=True
        ),
        SimpleField(
            name="series_id", type=SearchFieldDataType.String, filterable=True
        ),
        SimpleField(
            name="group_id", type=SearchFieldDataType.String, filterable=True
        ),
        SearchableField(name="topic_name", type=SearchFieldDataType.String),
        SearchableField(name="decision_text", type=SearchFieldDataType.String),
        SimpleField(name="owner", type=SearchFieldDataType.String, filterable=True),
        SimpleField(
            name="captured_at",
            type=SearchFieldDataType.DateTimeOffset,
            filterable=True,
            sortable=True,
        ),
        SearchField(
            name=VECTOR_FIELD,
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=VECTOR_DIM,
            vector_search_profile_name="hnsw-profile",
        ),
    ]
    vector_search = VectorSearch(
        algorithms=[HnswAlgorithmConfiguration(name="hnsw-config")],
        profiles=[
            VectorSearchProfile(
                name="hnsw-profile",
                algorithm_configuration_name="hnsw-config",
            )
        ],
    )
    index = SearchIndex(
        name=_index_name(),
        fields=fields,
        vector_search=vector_search,
    )
    async with SearchIndexClient(
        endpoint=s.azure_search_endpoint or "",
        credential=AzureKeyCredential(s.azure_search_key or ""),
    ) as client:
        await client.create_or_update_index(index)
    logger.info("decision_search.index_ensured", name=_index_name())


async def upsert_decision(decision: Decision) -> bool:
    """Search index に 1 件 upsert。embedding 必須。

    Search 未設定 / embedding 無し → 何もせず False。
    """
    if not _is_search_configured() or not decision.embedding:
        return False
    s = get_settings()
    from azure.core.credentials import AzureKeyCredential
    from azure.search.documents.aio import SearchClient

    doc = {
        "id": decision.id,
        "organizer_id": decision.organizer_id,
        "meeting_id": decision.meeting_id,
        "topic_id": decision.topic_id,
        "series_id": decision.series_id or "",
        "group_id": decision.group_id or "",
        "topic_name": decision.topic_name,
        "decision_text": decision.decision_text,
        "owner": decision.owner,
        "captured_at": decision.captured_at.isoformat(),
        VECTOR_FIELD: decision.embedding,
    }
    async with SearchClient(
        endpoint=s.azure_search_endpoint or "",
        index_name=_index_name(),
        credential=AzureKeyCredential(s.azure_search_key or ""),
    ) as client:
        result = await client.upload_documents(documents=[doc])
    succeeded = all(r.succeeded for r in result)
    if succeeded:
        logger.info("decision_search.upserted", id=decision.id)
    else:
        logger.warning("decision_search.upsert_partial", id=decision.id)
    return succeeded


async def _search_via_ai_search(
    *,
    query_embedding: list[float],
    organizer_id: str,
    series_id: str | None,
    group_id: str | None,
    top_k: int,
    repo: DecisionRepository,
) -> list[DecisionHit]:
    """AI Search path — vector 検索 → DecisionRepository で本体取得 → boost。"""
    s = get_settings()
    from azure.core.credentials import AzureKeyCredential
    from azure.search.documents.aio import SearchClient
    from azure.search.documents.models import VectorizedQuery

    vector_query = VectorizedQuery(
        vector=query_embedding,
        k_nearest_neighbors=top_k * 3,  # boost で順位入れ替わる余地
        fields=VECTOR_FIELD,
    )
    filter_expr = f"organizer_id eq '{organizer_id}'"

    raw_hits: list[tuple[str, float]] = []
    async with SearchClient(
        endpoint=s.azure_search_endpoint or "",
        index_name=_index_name(),
        credential=AzureKeyCredential(s.azure_search_key or ""),
    ) as client:
        response = await client.search(
            search_text=None,
            vector_queries=[vector_query],
            filter=filter_expr,
            top=top_k * 3,
            select=["id"],
        )
        async for raw in response:
            score = raw.get("@search.score") or 0.0
            raw_hits.append((raw["id"], float(score)))

    if not raw_hits:
        return []

    # 本体は Cosmos から取得 (Decision モデルとして使うため)
    hits: list[DecisionHit] = []
    for decision_id, base_score in raw_hits:
        d = await repo.get(decision_id, organizer_id)
        if d is None:
            continue
        final = apply_boost(base_score, d, series_id=series_id, group_id=group_id)
        hits.append(DecisionHit(decision=d, score=final))
    hits.sort(key=lambda h: h.score, reverse=True)
    return hits[:top_k]


# ===== numpy/Cosmos fallback path =====


async def _search_via_cosmos_fallback(
    *,
    query_embedding: list[float],
    organizer_id: str,
    series_id: str | None,
    group_id: str | None,
    top_k: int,
    within_days: int,
    repo: DecisionRepository,
) -> list[DecisionHit]:
    """Search 未設定時のフォールバック — Cosmos 全件 + cosine。

    organizer 1 人あたり ≤ 1000 decisions を想定。実会議の頻度 (週 5 件 × 各 5 決定 =
    年 1300 件) を考えても 90 日窓で十分小さい。
    """
    decisions = await repo.list_by_organizer(
        organizer_id, within_days=within_days, limit=1000
    )
    hits: list[DecisionHit] = []
    for d in decisions:
        if not d.embedding:
            continue
        sim = _cosine(query_embedding, d.embedding)
        final = apply_boost(sim, d, series_id=series_id, group_id=group_id)
        hits.append(DecisionHit(decision=d, score=final))
    hits.sort(key=lambda h: h.score, reverse=True)
    return hits[:top_k]


# ===== 公開 API =====


async def search_decisions(
    *,
    query_embedding: list[float],
    organizer_id: str,
    series_id: str | None = None,
    group_id: str | None = None,
    top_k: int = 5,
    within_days: int = 90,
    repo: DecisionRepository | None = None,
) -> list[DecisionHit]:
    """会議横断で類似 decision を検索する。

    AI Search 設定済 → HNSW vector search → boost。
    未設定 → Cosmos 全件 + cosine。
    どちらの path も同じ DecisionHit リストを返す。
    """
    if not query_embedding:
        return []
    repo = repo or DecisionRepository()
    if _is_search_configured():
        try:
            return await _search_via_ai_search(
                query_embedding=query_embedding,
                organizer_id=organizer_id,
                series_id=series_id,
                group_id=group_id,
                top_k=top_k,
                repo=repo,
            )
        except Exception as e:  # noqa: BLE001
            logger.warning("decision_search.ai_search_failed", error=str(e))
            # フォールバック (Search が一時的に死んでても止めない)
    return await _search_via_cosmos_fallback(
        query_embedding=query_embedding,
        organizer_id=organizer_id,
        series_id=series_id,
        group_id=group_id,
        top_k=top_k,
        within_days=within_days,
        repo=repo,
    )
