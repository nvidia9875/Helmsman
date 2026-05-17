"""Meeting endpoints — 会議の作成・取得・発言投入。"""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

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
from helmsman.agents.base import LLMAgent
from helmsman.core.logging import logger
from helmsman.core.pricing import calculate_cost_usd
from helmsman.core.usage import MeetingUsage
from helmsman.models.intervention import InterventionCandidate, InterventionDelivery
from helmsman.models.meeting import Meeting, MeetingMode, MeetingState, UserIntensity
from helmsman.models.participant import Participant
from helmsman.models.topic import Topic
from helmsman.models.utterance import Utterance
from helmsman.repositories.documents import DocumentRepository
from helmsman.repositories.meetings import MeetingRepository
from helmsman.services.rag import (
    fetch_document_excerpts_simple,
    retrieve_excerpts_for_goal,
)

from helmsman.api.security import require_api_key

router = APIRouter(
    prefix="/meetings",
    tags=["meetings"],
    dependencies=[Depends(require_api_key)],
)


# ---------- request / response schemas ----------

class StartMeetingRequest(BaseModel):
    """Bot 派遣セッションを開始するリクエスト。

    Helmsman は「会議を作る」ものではなく「既存 Teams 会議に Bot を派遣する」
    プロダクトなので、`teams_meeting_url` が主役。`goal` を入れると論点も
    分解されるが、入れなくても OK ("監視のみ" モード)。
    """
    organizer_id: str
    goal: str = Field(default="", max_length=500)
    mode: MeetingMode = MeetingMode.DECISION
    total_minutes: int = Field(default=60, ge=5, le=240)
    user_intensity: UserIntensity = UserIntensity.NORMAL
    # 継続セッション (任意): 指定すると前回の未解決論点を引き継ぐ
    parent_meeting_id: str | None = None
    # Teams 会議 URL (任意): 指定すると即時 Bot を派遣する
    teams_meeting_url: str | None = None


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


# ---------- helpers ----------

def _accumulate_usage(usage: MeetingUsage, agents: list[LLMAgent]) -> None:
    """各 agent の last_usage を Meeting.usage に積み上げる (in-place)。

    LLM を呼ばなかった agent や呼び出し失敗で last_usage が None のものは
    自然にスキップされる。
    """
    for agent in agents:
        record = agent.last_usage
        if record is None:
            continue
        cost_usd = calculate_cost_usd(record)
        usage.apply(record, cost_usd)


# ---------- dependency ----------

def get_repo() -> MeetingRepository:
    return MeetingRepository()


# ---------- endpoints ----------

@router.post("", response_model=Meeting, status_code=201)
async def start_meeting(
    req: StartMeetingRequest,
    repo: MeetingRepository = Depends(get_repo),
) -> Meeting:
    """ゴールから論点を分解して会議を開始する。

    `parent_meeting_id` 指定時は前回会議の未解決論点 (state != decided) を
    GoalDecomposer の context に注入し、series_id / series_index を引き継ぐ。
    """
    parent: Meeting | None = None
    inherited_topics: list[Topic] = []
    series_id: str | None = None
    series_index: int | None = None
    inherited_topic_ids: list[str] = []

    if req.parent_meeting_id:
        parent = await repo.get(req.parent_meeting_id, req.organizer_id)
        if not parent:
            raise HTTPException(404, "parent meeting not found")
        inherited_topics = [t for t in parent.topics if t.state.value != "decided"]
        inherited_topic_ids = [t.id for t in inherited_topics]
        series_id = parent.series_id or str(uuid4())
        series_index = (parent.series_index or 1) + 1

    # ゴールが入っていれば論点を分解。空なら「監視モード」(topics 無し) で開始
    decomposer = GoalDecomposer()
    topics: list[Topic] = []
    has_goal = bool(req.goal and req.goal.strip())
    if has_goal:
        try:
            topics = await decomposer.run(
                req.goal, req.mode, inherited_topics=inherited_topics or None
            )
        except Exception as e:  # noqa: BLE001
            logger.error(
                "start_meeting.decomposer_failed",
                goal=req.goal[:80],
                error=str(e),
                error_type=type(e).__name__,
            )
            topics = []

    meeting = Meeting(
        organizer_id=req.organizer_id,
        goal=req.goal,
        mode=req.mode,
        total_minutes=req.total_minutes,
        user_intensity=req.user_intensity,
        state=MeetingState.IN_PROGRESS,
        started_at=datetime.now(UTC),
        topics=topics,
        parent_meeting_id=req.parent_meeting_id,
        series_id=series_id,
        series_index=series_index,
        inherited_topic_ids=inherited_topic_ids,
        teams_meeting_url=req.teams_meeting_url,
    )
    if has_goal:
        _accumulate_usage(meeting.usage, [decomposer])
    await repo.create(meeting)

    # 親会議側に series_id を遡及付与 (シリーズ最初の継続時のみ)
    if parent and parent.series_id is None and series_id is not None:
        parent.series_id = series_id
        parent.series_index = 1
        await repo.upsert(parent)

    # Teams 会議 URL が渡されていれば即時 Bot 派遣 (フロントの 1-step UX 用)
    if req.teams_meeting_url:
        try:
            from helmsman.services.teams_bot import invite_bot_to_teams_meeting
            connection_id = await invite_bot_to_teams_meeting(
                meeting_id=meeting.id,
                organizer_id=req.organizer_id,
                teams_meeting_url=req.teams_meeting_url,
            )
            meeting.bot_call_connection_id = connection_id
            meeting.bot_status = "connecting"
            meeting.bot_last_event_at = datetime.now(UTC)
            await repo.upsert(meeting)
            logger.info(
                "start_meeting.bot_dispatched",
                meeting_id=meeting.id,
                call_connection_id=connection_id,
            )
        except Exception as e:  # noqa: BLE001
            # Bot 派遣失敗は致命ではない — 会議自体は作成済。後から /bot/invite で再試行可能
            logger.warning(
                "start_meeting.bot_dispatch_failed",
                meeting_id=meeting.id,
                error=str(e),
                error_type=type(e).__name__,
            )
            meeting.bot_status = "failed"
            await repo.upsert(meeting)

    return meeting


@router.get("", response_model=list[Meeting])
async def list_meetings(
    organizer_id: str,
    limit: int = 20,
    repo: MeetingRepository = Depends(get_repo),
) -> list[Meeting]:
    """主催者の最近の会議一覧 (新しい順)。「続きから」UI のソースデータ。"""
    return await repo.list_by_organizer(organizer_id, limit=limit)


class UsageSummaryByDay(BaseModel):
    date: str
    cost_usd: float
    total_tokens: int
    meeting_count: int


class UsageSummary(BaseModel):
    total_meetings: int
    total_cost_usd: float
    total_tokens: int
    avg_cost_per_meeting_usd: float
    by_day: list[UsageSummaryByDay]
    by_agent: dict[str, float]  # agent_name → cost_usd


@router.get("/usage/summary", response_model=UsageSummary)
async def get_usage_summary(
    organizer_id: str,
    days: int = 30,
    repo: MeetingRepository = Depends(get_repo),
) -> UsageSummary:
    """主催者の全会議を集計したコストサマリー (ランディング画面用)。"""
    meetings = await repo.list_by_organizer(organizer_id, limit=200)
    total_cost = 0.0
    total_tokens = 0
    by_agent: dict[str, float] = {}
    by_day: dict[str, dict] = {}
    counted = 0
    for m in meetings:
        if not m.started_at:
            continue
        # 日付キー (UTC)
        day = m.started_at.date().isoformat()
        bucket = by_day.setdefault(
            day, {"cost_usd": 0.0, "total_tokens": 0, "meeting_count": 0}
        )
        cost = m.usage.total_cost_usd
        bucket["cost_usd"] += cost
        bucket["total_tokens"] += m.usage.total_tokens
        bucket["meeting_count"] += 1
        total_cost += cost
        total_tokens += m.usage.total_tokens
        for agent_name, rollup in m.usage.by_agent.items():
            by_agent[agent_name] = by_agent.get(agent_name, 0.0) + rollup.cost_usd
        counted += 1

    sorted_days = sorted(by_day.items())[-days:]
    return UsageSummary(
        total_meetings=counted,
        total_cost_usd=round(total_cost, 6),
        total_tokens=total_tokens,
        avg_cost_per_meeting_usd=round(total_cost / counted, 6) if counted else 0.0,
        by_day=[
            UsageSummaryByDay(
                date=d,
                cost_usd=round(b["cost_usd"], 6),
                total_tokens=b["total_tokens"],
                meeting_count=b["meeting_count"],
            )
            for d, b in sorted_days
        ],
        by_agent={k: round(v, 6) for k, v in by_agent.items()},
    )


@router.get("/series/{series_id}", response_model=list[Meeting])
async def list_series_meetings(
    series_id: str,
    organizer_id: str,
    repo: MeetingRepository = Depends(get_repo),
) -> list[Meeting]:
    """同シリーズの全会議 (series_index 昇順)。"""
    return await repo.list_series(series_id, organizer_id)


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


@router.get("/{meeting_id}/usage", response_model=MeetingUsage)
async def get_meeting_usage(
    meeting_id: str,
    organizer_id: str,
    repo: MeetingRepository = Depends(get_repo),
) -> MeetingUsage:
    """1 会議の LLM token / コスト集計を返す。"""
    m = await repo.get(meeting_id, organizer_id)
    if not m:
        raise HTTPException(404, "meeting not found")
    return m.usage


@router.post("/{meeting_id}/redecompose", response_model=Meeting)
async def redecompose_meeting(
    meeting_id: str,
    organizer_id: str,
    repo: MeetingRepository = Depends(get_repo),
) -> Meeting:
    """添付文書を踏まえて論点を再分解する (RAG 付き GoalDecomposer)。

    新規文書のアップロード後に呼ぶ想定。Decision 状態が変わっている既存論点は
    捨ててしまうので、UI 側は実行確認モーダルを出すのが望ましい。
    """
    meeting = await repo.get(meeting_id, organizer_id)
    if not meeting:
        raise HTTPException(404, "meeting not found")

    doc_repo = DocumentRepository()
    excerpts = await retrieve_excerpts_for_goal(
        meeting_id=meeting_id,
        goal=meeting.goal,
        repo=doc_repo,
        usage_sink=meeting.usage,
    )

    inherited = [t for t in meeting.topics if t.state.value != "decided"]
    decomposer = GoalDecomposer()
    try:
        new_topics = await decomposer.run(
            meeting.goal,
            meeting.mode,
            inherited_topics=inherited or None,
            document_excerpts=excerpts or None,
        )
    except Exception as e:  # noqa: BLE001
        logger.error(
            "redecompose.failed",
            meeting_id=meeting_id,
            error=str(e),
            error_type=type(e).__name__,
        )
        # 失敗時は既存 topics をそのまま (新規論点は加えない)
        new_topics = meeting.topics
    meeting.topics = new_topics
    _accumulate_usage(meeting.usage, [decomposer])
    await repo.upsert(meeting)
    return meeting


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

    # 文書 RAG: 文書付き会議だと CoverageTracker に excerpt を流す (DOC-5)
    doc_excerpts: str | None = None
    if meeting.document_ids:
        try:
            doc_excerpts = await fetch_document_excerpts_simple(
                meeting_id=meeting_id, repo=DocumentRepository()
            ) or None
        except Exception as e:  # noqa: BLE001
            logger.warning("tick.doc_excerpts_failed", error=str(e))

    # 全 agent を並列実行。1 つが失敗しても他は続行 (return_exceptions=True)。
    results = await asyncio.gather(
        coverage.run(req.recent_utterances, meeting.topics, document_excerpts=doc_excerpts),
        steering.run(meeting, req.recent_utterances, meeting.topics),
        decision_capture.run(
            meeting, req.recent_utterances, meeting.topics, document_excerpts=doc_excerpts
        ),
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

    # LLM 呼び出しの usage を Meeting に積み上げる
    _accumulate_usage(
        meeting.usage,
        [coverage, steering, decision_capture, quiet, dissent],
    )

    # Arbiter
    arbiter = InterventionArbiter()
    chair = next((p for p in req.participants if p.id == req.chair_id), None)
    current = next(
        (p for p in req.participants if p.id == req.current_speaker_id), None
    )
    delivery = arbiter.decide(candidates, meeting, chair, current)

    if delivery:
        meeting.last_intervention_at = datetime.now(UTC)
        meeting.delivered_interventions.append(delivery)
        # 最新 20 件のみ保持 (Cosmos の document サイズ + UI スクロール量を抑える)
        meeting.delivered_interventions = meeting.delivered_interventions[-20:]

    await repo.upsert(meeting)

    return TickResponse(
        meeting=meeting,
        candidates=candidates,
        delivery=delivery,
    )
