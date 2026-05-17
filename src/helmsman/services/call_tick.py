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
        QuietActivator,
        SteeringAgent,
        TimeKeeper,
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

    coverage = CoverageTracker()
    steering = SteeringAgent()
    decision_capture = DecisionCapture()
    quiet = QuietActivator()
    dissent = DissentSurface()
    recent = session.utterances[-15:]

    results = await asyncio.gather(
        coverage.run(recent, meeting.topics),
        steering.run(meeting, recent, meeting.topics),
        decision_capture.run(meeting, recent, meeting.topics),
        quiet.run(meeting, participants, meeting.topics),
        dissent.run(meeting, recent),
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
    _decision_topic, decision_cand = decision_result
    quiet_cand = _ok(results[3])
    dissent_cand = _ok(results[4])

    candidates: list[InterventionCandidate] = []
    for c in (steering_cand, decision_cand, quiet_cand, dissent_cand):
        if c:
            candidates.append(c)
    tk = TimeKeeper().run(meeting)
    if tk:
        candidates.append(tk)

    # usage 集計
    for agent in (coverage, steering, decision_capture, quiet, dissent):
        record = agent.last_usage
        if record is None:
            continue
        meeting.usage.apply(record, calculate_cost_usd(record))

    arbiter = InterventionArbiter()
    delivery = arbiter.decide(candidates, meeting, chair, chair)
    if delivery:
        from datetime import UTC, datetime
        meeting.last_intervention_at = datetime.now(UTC)

    await repo.upsert(meeting)

    logger.info(
        "call.tick_done",
        meeting_id=session.meeting_id,
        pending_consumed=pending_added,
        candidates=len(candidates),
        delivered=delivery is not None,
        delivery_level=delivery.level if delivery else None,
    )

    # Phase C で TTS playback フックを足す:
    # if delivery and delivery.level == "L3":
    #     await play_intervention_audio(session, delivery)
