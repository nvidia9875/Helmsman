"""Meeting endpoints — 会議の作成・取得・発言投入。"""
from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

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
from helmsman.models.intervention import InterventionCandidate, InterventionDelivery
from helmsman.models.meeting import Meeting, MeetingMode, MeetingState, UserIntensity
from helmsman.models.participant import Participant
from helmsman.models.utterance import Utterance
from helmsman.repositories.meetings import MeetingRepository

from helmsman.api.security import require_api_key

router = APIRouter(
    prefix="/meetings",
    tags=["meetings"],
    dependencies=[Depends(require_api_key)],
)


# ---------- request / response schemas ----------

class StartMeetingRequest(BaseModel):
    organizer_id: str
    goal: str = Field(..., min_length=4, max_length=500)
    mode: MeetingMode = MeetingMode.DECISION
    total_minutes: int = Field(default=60, ge=5, le=240)
    user_intensity: UserIntensity = UserIntensity.NORMAL


class UtteranceRequest(BaseModel):
    speaker_id: str
    speaker_name: str | None = None
    text: str


class TickRequest(BaseModel):
    """1 サイクル: 直近発言 + 参加者統計を渡し、エージェントを全部動かす。"""

    recent_utterances: list[Utterance] = Field(default_factory=list)
    participants: list[Participant] = Field(default_factory=list)
    current_speaker_id: str | None = None
    chair_id: str | None = None


class TickResponse(BaseModel):
    meeting: Meeting
    candidates: list[InterventionCandidate]
    delivery: InterventionDelivery | None


# ---------- dependency ----------

def get_repo() -> MeetingRepository:
    return MeetingRepository()


# ---------- endpoints ----------

@router.post("", response_model=Meeting, status_code=201)
async def start_meeting(
    req: StartMeetingRequest,
    repo: MeetingRepository = Depends(get_repo),
) -> Meeting:
    """ゴールから論点を分解して会議を開始する。"""
    decomposer = GoalDecomposer()
    topics = await decomposer.run(req.goal, req.mode)
    meeting = Meeting(
        organizer_id=req.organizer_id,
        goal=req.goal,
        mode=req.mode,
        total_minutes=req.total_minutes,
        user_intensity=req.user_intensity,
        state=MeetingState.IN_PROGRESS,
        started_at=datetime.now(UTC),
        topics=topics,
    )
    await repo.create(meeting)
    return meeting


@router.get("/{meeting_id}", response_model=Meeting)
async def get_meeting(
    meeting_id: str,
    organizer_id: str,
    repo: MeetingRepository = Depends(get_repo),
) -> Meeting:
    m = await repo.get(meeting_id, organizer_id)
    if not m:
        raise HTTPException(404, "meeting not found")
    return m


@router.post("/{meeting_id}/tick", response_model=TickResponse)
async def tick(
    meeting_id: str,
    organizer_id: str,
    req: TickRequest,
    repo: MeetingRepository = Depends(get_repo),
) -> TickResponse:
    """1 サイクル: 全エージェントを並列実行し Arbiter で 1 介入決定する。

    クライアントは数十秒に 1 回これを呼ぶ想定。
    """
    meeting = await repo.get(meeting_id, organizer_id)
    if not meeting:
        raise HTTPException(404, "meeting not found")

    # --- 並列実行は asyncio.gather で
    import asyncio

    coverage = CoverageTracker()
    steering = SteeringAgent()
    decision_capture = DecisionCapture()
    quiet = QuietActivator()
    dissent = DissentSurface()

    # 全 agent を並列実行。1 つが失敗しても他は続行 (return_exceptions=True)。
    results = await asyncio.gather(
        coverage.run(req.recent_utterances, meeting.topics),
        steering.run(meeting, req.recent_utterances, meeting.topics),
        decision_capture.run(meeting, req.recent_utterances, meeting.topics),
        quiet.run(meeting, req.participants, meeting.topics),
        dissent.run(meeting, req.recent_utterances),
        return_exceptions=True,
    )

    def _ok(r: Any) -> Any:
        """例外なら None / 構造化ログを出す。"""
        if isinstance(r, Exception):
            from helmsman.core.logging import logger
            logger.warning("tick.agent_failed", error=str(r), error_type=type(r).__name__)
            return None
        return r

    updated_topics = _ok(results[0]) or meeting.topics
    steering_cand = _ok(results[1])
    decision_result = _ok(results[2]) or (None, None)
    quiet_cand = _ok(results[3])
    dissent_cand = _ok(results[4])

    meeting.topics = updated_topics
    _decision_topic, decision_cand = decision_result

    # 候補集約
    candidates: list[InterventionCandidate] = []
    if steering_cand:
        candidates.append(steering_cand)
    if decision_cand:
        candidates.append(decision_cand)
    if quiet_cand:
        candidates.append(quiet_cand)
    if dissent_cand:
        candidates.append(dissent_cand)

    # TimeKeeper (rule-based)
    tk = TimeKeeper().run(meeting)
    if tk:
        candidates.append(tk)

    # Arbiter
    arbiter = InterventionArbiter()
    chair = next((p for p in req.participants if p.id == req.chair_id), None)
    current = next(
        (p for p in req.participants if p.id == req.current_speaker_id), None
    )
    delivery = arbiter.decide(candidates, meeting, chair, current)

    if delivery:
        meeting.last_intervention_at = datetime.now(UTC)

    await repo.upsert(meeting)

    return TickResponse(
        meeting=meeting,
        candidates=candidates,
        delivery=delivery,
    )
