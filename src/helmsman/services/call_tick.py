"""CallSession のバッファ済 utterance を tick エンドポイント相当のロジックに流し込む。

API router の `POST /tick` と同じ処理を内部関数として呼ぶ — bot 経由なので
HTTP を経由する必要はない。tick 終了後、pending カウンタをリセット。
"""
from __future__ import annotations

import asyncio
import time

from helmsman.core.logging import logger
from helmsman.services.call_buffer import CallSession

# 連続 tick 防止: 同一 session で最低 N 秒空ける
MIN_TICK_GAP_SECONDS = 8.0


async def maybe_trigger_tick(session: CallSession, *, force: bool = False) -> None:
    """tick を発火すべきか判定して、必要なら走らせる。

    force=True (timer 経由) でも、min gap を満たさなければスキップ。
    """
    now = time.monotonic()
    if session.last_tick_at is not None:
        elapsed = now - session.last_tick_at
        if elapsed < MIN_TICK_GAP_SECONDS:
            if not force:
                logger.debug(
                    "call.tick_skipped_gap",
                    call_id=session.call_connection_id,
                    gap=elapsed,
                )
            return

    if session.pending_since_last_tick == 0 and not force:
        return

    pending = session.pending_since_last_tick
    session.pending_since_last_tick = 0
    session.last_tick_at = now

    # 並列で走らせ、結果を待たない (次の audio chunk を blockしない)
    asyncio.create_task(_run_tick(session, pending_added=pending))


async def _run_tick(session: CallSession, *, pending_added: int) -> None:
    """既存 tick endpoint と同じパイプライン (5 agents + arbiter) を内部呼び出し。"""
    # 依存 import: agents / repo / arbiter は router 経由ではなく直接呼ぶ
    from helmsman.agents import (
        CoverageTracker,
        DecisionCapture,
        DissentSurface,
        InterventionArbiter,
        MemoryRetriever,
        QuietActivator,
        SteeringAgent,
        TimeKeeper,
        ToneAgent,
    )
    from helmsman.core.pricing import calculate_cost_usd
    from helmsman.models.intervention import InterventionCandidate
    from helmsman.models.participant import Participant
    from helmsman.repositories.meetings import MeetingRepository

    repo = MeetingRepository()
    meeting = await repo.get(session.meeting_id, session.organizer_id)
    if not meeting:
        logger.warning(
            "call.tick_meeting_missing",
            meeting_id=session.meeting_id,
        )
        return

    # bot 経由なので participant info は限定的。chair は organizer とする。
    chair = Participant(
        id=session.organizer_id,
        meeting_id=session.meeting_id,
        display_name="Chair",
        is_chair=True,
        joined_at=meeting.started_at or meeting.last_intervention_at,
        total_speak_seconds=sum(u.duration_sec for u in session.utterances),
        utterance_count=len(session.utterances),
    )
    participants = [chair]

    # Timekeeper: 開始から N 分経過した alert を発火 (bot が音声で読み上げる)
    await _maybe_fire_timekeeper(meeting, session)

    coverage = CoverageTracker()
    steering = SteeringAgent()
    decision_capture = DecisionCapture()
    quiet = QuietActivator()
    dissent = DissentSurface()
    memory = MemoryRetriever()
    tone = ToneAgent()
    recent = session.utterances[-15:]

    # 文書 RAG (DOC-5): bot 会議でも CoverageTracker に excerpt を渡す
    doc_excerpts: str | None = None
    if meeting.document_ids:
        try:
            from helmsman.repositories.documents import DocumentRepository
            from helmsman.services.rag import fetch_document_excerpts_simple

            doc_excerpts = await fetch_document_excerpts_simple(
                meeting_id=meeting.id, repo=DocumentRepository()
            ) or None
        except Exception as e:  # noqa: BLE001
            logger.warning("call.doc_excerpts_failed", error=str(e))

    results = await asyncio.gather(
        coverage.run(recent, meeting.topics, document_excerpts=doc_excerpts),
        steering.run(meeting, recent, meeting.topics),
        decision_capture.run(
            meeting, recent, meeting.topics, document_excerpts=doc_excerpts
        ),
        quiet.run(meeting, participants, meeting.topics),
        dissent.run(meeting, recent),
        memory.run(meeting, recent, usage_sink=meeting.usage),
        tone.run(meeting, recent, participants=participants),
        return_exceptions=True,
    )

    def _ok(r):  # noqa: ANN001
        if isinstance(r, Exception):
            logger.warning("call.tick_agent_failed", error=str(r))
            return None
        return r

    meeting.topics = _ok(results[0]) or meeting.topics
    steering_cand = _ok(results[1])
    decision_result = _ok(results[2]) or (None, None)
    decision_topic, decision_cand = decision_result
    quiet_cand = _ok(results[3])
    dissent_cand = _ok(results[4])
    memory_cand = _ok(results[5])
    tone_cand = _ok(results[6])

    # Phase 7: DecisionCapture 確定時、write-through で Cosmos + Search に保存
    if decision_topic is not None and decision_cand is not None:
        try:
            from helmsman.services.decision_persistence import persist_decision
            await persist_decision(
                meeting=meeting,
                topic=decision_topic,
                candidate=decision_cand,
                usage_sink=meeting.usage,
            )
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "call.decision_persist_failed", error=str(e),
                topic_id=decision_topic.id,
            )

    candidates: list[InterventionCandidate] = []
    # 議論方向確認 (Steering) は設定で OFF にできる
    for c in (steering_cand if meeting.steering_enabled else None, decision_cand,
              quiet_cand, dissent_cand, memory_cand, tone_cand):
        if c:
            candidates.append(c)
    tk = TimeKeeper().run(meeting)
    if tk:
        candidates.append(tk)

    # usage 集計
    for agent in (coverage, steering, decision_capture, quiet, dissent, memory, tone):
        record = agent.last_usage
        if record is None:
            continue
        meeting.usage.apply(record, calculate_cost_usd(record))

    # transcript を永続化 (bot disconnect 後でも report 生成・参照可能に)
    # session.utterances は in-memory バッファで disconnect 時に消えるため、
    # 直近 500 件を Cosmos の meeting.transcript にコピーして残す。
    meeting.transcript = list(session.utterances[-500:])

    arbiter = InterventionArbiter()
    delivery = arbiter.decide(candidates, meeting, chair, chair)
    if delivery:
        from datetime import UTC, datetime
        meeting.last_intervention_at = datetime.now(UTC)
        meeting.delivered_interventions.append(delivery)
        meeting.delivered_interventions = meeting.delivered_interventions[-20:]
        # Phase 7: MemoryRetriever が配信されたら surfaced リストに追加 (dedup)
        if (
            delivery.agent == "MemoryRetriever"
            and delivery.evidence_quote
            and delivery.evidence_quote not in meeting.surfaced_decision_ids
        ):
            meeting.surfaced_decision_ids.append(delivery.evidence_quote)
            meeting.surfaced_decision_ids = meeting.surfaced_decision_ids[-50:]

    await repo.upsert(meeting)

    logger.info(
        "call.tick_done",
        meeting_id=session.meeting_id,
        pending_consumed=pending_added,
        candidates=len(candidates),
        delivered=delivery is not None,
        delivery_level=delivery.level if delivery else None,
    )

    # Phase C / M.D: L3 (音声介入) → 会議内 TTS 再生
    if delivery and delivery.level == "L3":
        text = _build_l3_utterance(delivery.content, delivery.reason)
        logger.info(
            "call.l3_speak",
            meeting_id=session.meeting_id,
            text=text[:80],
            agent=delivery.agent,
        )
        # 2 つの経路を session の状態で判別:
        # - media_ws あり (旧 ACS bidirectional WebSocket) → 旧パス
        # - media_ws なし (Graph Calling service-hosted) → playPrompt API
        if session.media_ws is not None:
            from helmsman.services.tts import speak_into_call
            asyncio.create_task(speak_into_call(session.media_ws, text))
        else:
            from helmsman.services.graph_play_prompt import play_text_in_graph_call
            asyncio.create_task(
                play_text_in_graph_call(session.call_connection_id, text)
            )


def _build_l3_utterance(content: str, reason: str | None) -> str:
    """会議で読み上げる短文を組み立てる。reason は付けない (long 過ぎる)。"""
    return content.strip()


async def _maybe_fire_timekeeper(meeting, session: CallSession) -> None:  # type: ignore[no-untyped-def]
    """会議開始から N 分経過した alert を一回だけ発火する。

    fired=False かつ enabled=True かつ elapsed_min >= minutes_from_start を満たす
    alert を全部読み上げる。発火後は fired=True を Cosmos に書き戻し。
    """
    if not meeting.started_at or not meeting.timekeeper_alerts:
        return
    from datetime import UTC, datetime
    elapsed_min = (datetime.now(UTC) - meeting.started_at).total_seconds() / 60.0

    fired_any = False
    for alert in meeting.timekeeper_alerts:
        if alert.fired or not alert.enabled:
            continue
        if elapsed_min < alert.minutes_from_start:
            continue
        # 発火
        alert.fired = True
        alert.fired_at = datetime.now(UTC)
        fired_any = True
        logger.info(
            "call.timekeeper_fire",
            meeting_id=meeting.id,
            alert_id=alert.id,
            elapsed_min=round(elapsed_min, 1),
            target_min=alert.minutes_from_start,
            message=alert.message[:80],
        )
        # 音声発火 (session.media_ws が無い = Graph 経路)
        if session.media_ws is not None:
            from helmsman.services.tts import speak_into_call
            asyncio.create_task(speak_into_call(session.media_ws, alert.message))
        else:
            from helmsman.services.graph_play_prompt import play_text_in_graph_call
            asyncio.create_task(
                play_text_in_graph_call(session.call_connection_id, alert.message)
            )

    if fired_any:
        # fired フラグを Cosmos に書き戻し
        from helmsman.repositories.meetings import MeetingRepository
        try:
            await MeetingRepository().upsert(meeting)
        except Exception as e:  # noqa: BLE001
            logger.warning("call.timekeeper_save_failed", error=str(e))
