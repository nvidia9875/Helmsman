"""Decisions endpoints — Phase 7 (会議横断記憶) の読み取り API。

UI の History ページ / MemoryEchoCard が叩く。
書き込みは tick / call_tick 側の write-through (decision_persistence.py) のみ。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from helmsman.api.security import require_api_key
from helmsman.core.logging import logger
from helmsman.models.decision import Decision
from helmsman.repositories.decisions import DecisionRepository
from helmsman.services.decision_search import DecisionHit, search_decisions
from helmsman.services.embeddings import embed_texts

router = APIRouter(
    prefix="/decisions",
    tags=["decisions"],
    dependencies=[Depends(require_api_key)],
)


def get_repo() -> DecisionRepository:
    return DecisionRepository()


class DecisionListResponse(BaseModel):
    """ID で過去 decision を引いて返す軽量レスポンス (embedding は外す)。"""

    id: str
    meeting_id: str
    topic_id: str
    topic_name: str
    decision_text: str
    owner: str
    deadline: str
    evidence_quote: str | None
    series_id: str | None
    group_id: str | None
    confidence: float
    captured_at: str

    @classmethod
    def from_decision(cls, d: Decision) -> DecisionListResponse:
        return cls(
            id=d.id,
            meeting_id=d.meeting_id,
            topic_id=d.topic_id,
            topic_name=d.topic_name,
            decision_text=d.decision_text,
            owner=d.owner,
            deadline=d.deadline,
            evidence_quote=d.evidence_quote,
            series_id=d.series_id,
            group_id=d.group_id,
            confidence=d.confidence,
            captured_at=d.captured_at.isoformat(),
        )


class DecisionSearchHit(DecisionListResponse):
    """検索結果 — score 付き。"""

    score: float


class DecisionSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    organizer_id: str
    series_id: str | None = None
    group_id: str | None = None
    top_k: int = Field(default=10, ge=1, le=50)
    within_days: int = Field(default=90, ge=1, le=3650)


@router.get("", response_model=list[DecisionListResponse])
async def list_decisions(
    organizer_id: str,
    series_id: str | None = None,
    group_id: str | None = None,
    within_days: int = 90,
    limit: int = 100,
    repo: DecisionRepository = Depends(get_repo),
) -> list[DecisionListResponse]:
    """History ページ用 — 主催者の decision を新しい順に。

    series_id / group_id が指定されればフィルタ。両方指定時は series_id 優先。
    """
    if series_id:
        items = await repo.list_by_series(series_id, organizer_id, limit=limit)
    elif group_id:
        items = await repo.list_by_group(group_id, organizer_id, limit=limit)
    else:
        items = await repo.list_by_organizer(
            organizer_id, within_days=within_days, limit=limit
        )
    return [DecisionListResponse.from_decision(d) for d in items]


@router.get("/by-meeting/{meeting_id}", response_model=list[DecisionListResponse])
async def list_decisions_by_meeting(
    meeting_id: str,
    organizer_id: str,
    repo: DecisionRepository = Depends(get_repo),
) -> list[DecisionListResponse]:
    """会議詳細ページ: その会議で確定した decision 一覧。"""
    items = await repo.list_by_meeting(meeting_id, organizer_id)
    return [DecisionListResponse.from_decision(d) for d in items]


@router.get("/{decision_id}", response_model=DecisionListResponse)
async def get_decision(
    decision_id: str,
    organizer_id: str,
    repo: DecisionRepository = Depends(get_repo),
) -> DecisionListResponse:
    d = await repo.get(decision_id, organizer_id)
    if d is None:
        raise HTTPException(404, "decision not found")
    return DecisionListResponse.from_decision(d)


@router.post("/search", response_model=list[DecisionSearchHit])
async def search_decisions_endpoint(
    req: DecisionSearchRequest,
    repo: DecisionRepository = Depends(get_repo),
) -> list[DecisionSearchHit]:
    """自然言語で過去決定を検索する (History ページの検索バー用)。

    クエリ文字列を embed → search_decisions (AI Search or numpy fallback) → top_k。
    """
    vectors, _usage = await embed_texts([req.query])
    if not vectors:
        logger.warning("decisions.search_embed_empty", q=req.query[:50])
        return []
    hits: list[DecisionHit] = await search_decisions(
        query_embedding=vectors[0],
        organizer_id=req.organizer_id,
        series_id=req.series_id,
        group_id=req.group_id,
        top_k=req.top_k,
        within_days=req.within_days,
        repo=repo,
    )
    out: list[DecisionSearchHit] = []
    for h in hits:
        base = DecisionListResponse.from_decision(h.decision).model_dump()
        out.append(DecisionSearchHit(score=h.score, **base))
    return out
