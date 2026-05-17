"""オフライン評価のオーケストレータ。

Cosmos / Teams / ACS を介さず in-memory Meeting に対して既存 8 agents + Arbiter
を回す。Utterance ストリームを受け取り、N 秒ごと (音声時間軸) に tick を発火。
全 tick の入出力と最終状態を構造化して返す。
"""
from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

from helmsman.agents import (
    CoverageTracker,
    DecisionCapture,
    DissentSurface,
    GoalDecomposer,
    InterventionArbiter,
    QuietActivator,
    SteeringAgent,
    TimeKeeper,
)
from helmsman.agents.base import LLMAgent
from helmsman.core.logging import logger
from helmsman.core.pricing import calculate_cost_usd
from helmsman.models.intervention import InterventionCandidate, InterventionDelivery
from helmsman.models.meeting import (
    Meeting,
    MeetingMode,
    MeetingState,
    UserIntensity,
)
from helmsman.models.participant import Participant
from helmsman.models.utterance import Utterance


@dataclass
class TickRecord:
    """1 tick の入出力スナップショット (report.md / ticks.jsonl 用)。"""

    index: int
    audio_offset_sec: float
    wall_elapsed_sec: float
    recent_utterance_count: int
    candidate_count: int
    delivered: InterventionDelivery | None
    topic_states: dict[str, int]
    tick_latency_sec: float


@dataclass
class EvalResult:
    """評価実行全体の結果。"""

    meeting: Meeting
    utterances: list[Utterance]
    ticks: list[TickRecord]
    all_candidates: list[InterventionCandidate] = field(default_factory=list)
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    finished_at: datetime | None = None
    audio_duration_sec: float = 0.0

    @property
    def wall_duration_sec(self) -> float:
        if self.finished_at is None:
            return 0.0
        return (self.finished_at - self.started_at).total_seconds()


def _accumulate_usage(meeting: Meeting, agents: list[LLMAgent]) -> None:
    for agent in agents:
        record = agent.last_usage
        if record is None:
            continue
        meeting.usage.apply(record, calculate_cost_usd(record))


async def _run_one_tick(
    meeting: Meeting,
    *,
    recent: list[Utterance],
    participants: list[Participant],
    doc_excerpts: str | None,
) -> tuple[list[InterventionCandidate], InterventionDelivery | None]:
    """1 tick: 5 agents + TimeKeeper + Arbiter。meeting を in-place 更新。"""
    coverage = CoverageTracker()
    steering = SteeringAgent()
    decision_capture = DecisionCapture()
    quiet = QuietActivator()
    dissent = DissentSurface()

    results = await asyncio.gather(
        coverage.run(recent, meeting.topics, document_excerpts=doc_excerpts),
        steering.run(meeting, recent, meeting.topics),
        decision_capture.run(
            meeting, recent, meeting.topics, document_excerpts=doc_excerpts
        ),
        quiet.run(meeting, participants, meeting.topics),
        dissent.run(meeting, recent),
        return_exceptions=True,
    )

    def _ok(r):  # noqa: ANN001
        if isinstance(r, Exception):
            logger.warning("eval.agent_failed", error=str(r), error_type=type(r).__name__)
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

    _accumulate_usage(meeting, [coverage, steering, decision_capture, quiet, dissent])

    arbiter = InterventionArbiter()
    chair = participants[0] if participants else None
    delivery = arbiter.decide(candidates, meeting, chair, chair)
    if delivery:
        meeting.last_intervention_at = datetime.now(UTC)
        meeting.delivered_interventions.append(delivery)
        meeting.delivered_interventions = meeting.delivered_interventions[-50:]

    return candidates, delivery


def _topic_state_histogram(meeting: Meeting) -> dict[str, int]:
    hist: dict[str, int] = {}
    for t in meeting.topics:
        key = t.state.value if hasattr(t.state, "value") else str(t.state)
        hist[key] = hist.get(key, 0) + 1
    return hist


async def run_eval(
    utterance_stream: AsyncIterator[Utterance],
    *,
    goal: str = "",
    mode: MeetingMode = MeetingMode.DECISION,
    intensity: UserIntensity = UserIntensity.NORMAL,
    total_minutes: int = 60,
    tick_every_sec: float = 30.0,
    chair_id: str = "eval-chair",
    audio_duration_sec: float = 0.0,
) -> EvalResult:
    """utterance_stream を消費し、定期的に tick を発火、最終結果を返す。

    時間軸:
      - tick の発火間隔は **音声時間軸** (utterance.duration_sec の累積)。
        実時間ではない (音声を一気に流し込めるので)。
    """
    run_started_at = datetime.now(UTC)
    meeting = Meeting(
        id=str(uuid4()),
        organizer_id="eval",
        goal=goal,
        mode=mode,
        user_intensity=intensity,
        total_minutes=total_minutes,
        state=MeetingState.IN_PROGRESS,
        started_at=run_started_at,
    )

    decomposer_used = False
    if goal.strip():
        try:
            decomposer = GoalDecomposer()
            meeting.topics = await decomposer.run(goal, mode)
            _accumulate_usage(meeting, [decomposer])
            decomposer_used = True
        except Exception as e:  # noqa: BLE001
            logger.warning("eval.decomposer_failed", error=str(e))

    chair = Participant(
        id=chair_id,
        meeting_id=meeting.id,
        display_name="Chair",
        is_chair=True,
        joined_at=meeting.started_at,
    )
    participants = [chair]

    utterances: list[Utterance] = []
    ticks: list[TickRecord] = []
    all_candidates: list[InterventionCandidate] = []
    started_wall = time.monotonic()
    audio_offset_at_last_tick = 0.0
    audio_offset_accum = 0.0

    async def maybe_tick(force: bool = False) -> None:
        nonlocal audio_offset_at_last_tick
        if not utterances and not force:
            return
        # tick 間隔チェック (音声時間軸)
        gap = audio_offset_accum - audio_offset_at_last_tick
        if not force and gap < tick_every_sec:
            return

        recent = utterances[-15:]
        chair.total_speak_seconds = sum(u.duration_sec for u in utterances)
        chair.utterance_count = len(utterances)

        tick_start = time.monotonic()
        candidates, delivery = await _run_one_tick(
            meeting,
            recent=recent,
            participants=participants,
            doc_excerpts=None,
        )
        tick_latency = time.monotonic() - tick_start
        all_candidates.extend(candidates)

        ticks.append(
            TickRecord(
                index=len(ticks),
                audio_offset_sec=audio_offset_accum,
                wall_elapsed_sec=time.monotonic() - started_wall,
                recent_utterance_count=len(recent),
                candidate_count=len(candidates),
                delivered=delivery,
                topic_states=_topic_state_histogram(meeting),
                tick_latency_sec=tick_latency,
            )
        )
        audio_offset_at_last_tick = audio_offset_accum
        logger.info(
            "eval.tick_done",
            tick_index=ticks[-1].index,
            candidates=len(candidates),
            delivered=delivery is not None,
            latency=round(tick_latency, 2),
        )

    async for utterance in utterance_stream:
        utterances.append(utterance)
        audio_offset_accum += utterance.duration_sec
        await maybe_tick()

    # 最終 tick (force=True、残りを必ず処理)
    await maybe_tick(force=True)

    meeting.state = MeetingState.CONCLUDED
    meeting.ended_at = datetime.now(UTC)

    logger.info(
        "eval.completed",
        utterance_count=len(utterances),
        tick_count=len(ticks),
        decomposer_used=decomposer_used,
        topics=len(meeting.topics),
        delivered_total=len(meeting.delivered_interventions),
        total_cost_usd=round(meeting.usage.total_cost_usd, 4),
    )

    return EvalResult(
        meeting=meeting,
        utterances=utterances,
        ticks=ticks,
        all_candidates=all_candidates,
        started_at=run_started_at,
        finished_at=datetime.now(UTC),
        audio_duration_sec=audio_duration_sec or audio_offset_accum,
    )
