"""Decision の write-through 永続化 (Phase 7)。

DecisionCapture が confidence ≥ 0.7 で topic を DECIDED に遷移させた直後、
tick 側からこの関数を 1 発呼ぶ:

    await persist_decision(meeting, topic, candidate, usage_sink=meeting.usage)

これで以下が起きる:
  1. Decision を Pydantic 化 (deterministic id = meeting_id:topic_id)
  2. embed_texts でベクトル化
  3. DecisionRepository.upsert (Cosmos)
  4. decision_search.upsert_decision (AI Search、未設定なら no-op)

設計判断 (ADR-102):
  - 同一トピックが議論内で再合意された時は upsert で更新 → 重複なし
  - embed コストを抑えるため、同一トピックの embed_text に変化が無ければ
    既存 embedding を流用 (このモジュールでは判定せず、上位で skip 判定)
  - 失敗してもクリティカルではない (会議は続行)、warning ログのみ

DecisionCapture 自体は知らない (single-purpose を保つ)。
"""
from __future__ import annotations

from helmsman.core.logging import logger
from helmsman.core.pricing import calculate_cost_usd
from helmsman.core.usage import MeetingUsage
from helmsman.models.decision import Decision
from helmsman.models.intervention import InterventionCandidate
from helmsman.models.meeting import Meeting
from helmsman.models.topic import Topic
from helmsman.repositories.decisions import DecisionRepository
from helmsman.services.decision_search import upsert_decision
from helmsman.services.embeddings import embed_texts


async def persist_decision(
    *,
    meeting: Meeting,
    topic: Topic,
    candidate: InterventionCandidate,
    usage_sink: MeetingUsage | None = None,
    repo: DecisionRepository | None = None,
) -> Decision | None:
    """DecisionCapture が確定させた決定を Cosmos + AI Search に保存する。

    candidate.content は "決定: X (担当: Y, 期日: Z)" の形式 (decision_capture.py)。
    そこから decision_text / owner / deadline を抽出するのは難しいので、
    本関数では構造化フィールドは topic 由来のものを優先する。
    candidate は evidence_quote と confidence を取るのに使う。

    Returns:
        作成 or 更新された Decision、失敗時は None。
    """
    repo = repo or DecisionRepository()
    decision_id = Decision.make_id(meeting.id, topic.id)

    decision_text = (topic.evidence_quote or "").strip() or candidate.content
    embed_text = Decision.build_embed_text(
        topic_name=topic.name,
        decision_text=decision_text,
        owner="",  # candidate.content から parse は brittle、UI 側で後付け
        evidence_quote=candidate.evidence_quote,
    )

    # 1) embedding
    embedding: list[float] | None = None
    try:
        vectors, usage = await embed_texts([embed_text])
        if usage and usage_sink is not None:
            usage_sink.apply(usage, calculate_cost_usd(usage))
        if vectors:
            embedding = vectors[0]
    except Exception as e:  # noqa: BLE001
        logger.warning("decision_persist.embed_failed", error=str(e))
        # embedding 無くても decision 自体は保存する (後で再 embed 可)

    # 2) Decision 組み立て
    decision = Decision(
        id=decision_id,
        organizer_id=meeting.organizer_id,
        meeting_id=meeting.id,
        topic_id=topic.id,
        topic_name=topic.name,
        decision_text=decision_text,
        evidence_quote=candidate.evidence_quote,
        series_id=meeting.series_id,
        group_id=meeting.group_id,
        embedding=embedding,
        embed_text=embed_text,
        confidence=candidate.confidence,
    )

    # 3) Cosmos upsert
    try:
        await repo.upsert(decision)
    except Exception as e:  # noqa: BLE001
        logger.warning(
            "decision_persist.cosmos_failed",
            decision_id=decision_id,
            error=str(e),
        )
        return None

    # 4) AI Search upsert (設定済みのみ、未設定なら no-op で false)
    try:
        await upsert_decision(decision)
    except Exception as e:  # noqa: BLE001
        logger.warning(
            "decision_persist.search_failed",
            decision_id=decision_id,
            error=str(e),
        )
        # 検索は無くても Cosmos 側は成功してる → numpy フォールバックで読める

    logger.info(
        "decision_persist.done",
        meeting_id=meeting.id,
        topic_id=topic.id,
        topic_name=topic.name,
        has_embedding=embedding is not None,
    )
    return decision
