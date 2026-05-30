"""Meeting endpoints — 会議の作成・取得・発言投入。"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from helmsman.agents import (
    CoverageTracker,
    DecisionCapture,
    DissentSurface,
    GoalDecomposer,
    InterventionArbiter,
    MeetingReportGenerator,
    MemoryRetriever,
    QuietActivator,
    SteeringAgent,
    TimeKeeper,
    ToneAgent,
)
from helmsman.agents.base import LLMAgent
from helmsman.api.security import require_api_key
from helmsman.core.logging import logger
from helmsman.core.pricing import calculate_cost_usd
from helmsman.core.usage import MeetingUsage
from helmsman.models.intervention import InterventionCandidate, InterventionDelivery
from helmsman.models.meeting import Meeting, MeetingMode, MeetingState, UserIntensity
from helmsman.models.participant import Participant
from helmsman.models.report import MeetingReport
from helmsman.models.topic import Topic
from helmsman.models.utterance import Utterance
from helmsman.repositories.documents import DocumentRepository
from helmsman.repositories.meetings import MeetingRepository
from helmsman.repositories.reports import MeetingReportRepository
from helmsman.services.rag import (
    fetch_document_excerpts_simple,
    retrieve_excerpts_for_goal,
)

router = APIRouter(
    prefix="/meetings",
    tags=["meetings"],
    dependencies=[Depends(require_api_key)],
)

# Bot 状態が in_call/connecting/joining のまま、Graph webhook が
# この秒数以上届かなければ stale と判定し、自動で disconnected に書き戻す。
# 10 分: Graph の通常イベント間隔より十分長く、誤判定を避けられる閾値。
BOT_STALE_TIMEOUT_SEC = 600


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
    # グループ所属 (任意): 指定するとグループ文書も AI に流れる
    group_id: str | None = None
    # AI ファシリテーター名 (任意、UI ヘッダー + agent prompt に使う)
    facilitator_name: str | None = None


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


class GenerateReportRequest(BaseModel):
    """会議終了後レポートの生成リクエスト。

    template / memo はどちらも任意。両方空ならデフォルト構成で生成。
    両方与えるとテンプレ章立て + メモを最優先情報源として尊重して合成。
    """

    template: str | None = Field(
        default=None,
        max_length=20_000,
        description="ユーザー提供のレポートテンプレート (markdown / プレーンテキスト)",
    )
    memo: str | None = Field(
        default=None,
        max_length=20_000,
        description="ユーザーが会議中に取った手書きメモ。最優先情報源として扱う",
    )
    utterances: list[Utterance] = Field(
        default_factory=list,
        description="発言ログ (任意)。空でも topics.evidence_quote だけで多くの場合充足。",
    )


class GenerateReportResponse(BaseModel):
    id: str
    meeting_id: str
    report_markdown: str
    generated_at: datetime
    template_used: bool
    memo_used: bool
    utterances_included: int


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
        # デモ用: 常に AGGRESSIVE で派遣 (介入頻度↑・閾値0・音声を時間条件なしで発火)。
        # req.user_intensity は無視して固定。通常運用に戻すなら req.user_intensity に戻す。
        user_intensity=UserIntensity.AGGRESSIVE,
        state=MeetingState.IN_PROGRESS,
        started_at=datetime.now(UTC),
        topics=topics,
        parent_meeting_id=req.parent_meeting_id,
        series_id=series_id,
        series_index=series_index,
        inherited_topic_ids=inherited_topic_ids,
        teams_meeting_url=req.teams_meeting_url,
        group_id=req.group_id,
        facilitator_name=(req.facilitator_name or "").strip() or "Helmsman",
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

    # Stale auto-disconnect: Graph webhook が落ちて bot_status が in_call/connecting
    # で固まる現象への防御。bot_last_event_at から閾値以上経過していたら
    # 自動で disconnected に書き戻す。
    # (本来は Graph 側が常にイベントを送るが、deploy 中の取りこぼし等で
    # 状態不整合になるケースがある)
    if (
        m.bot_status in {"in_call", "connecting", "joining"}
        and m.bot_last_event_at is not None
    ):
        elapsed = (datetime.now(UTC) - m.bot_last_event_at).total_seconds()
        if elapsed > BOT_STALE_TIMEOUT_SEC:
            m.bot_status = "disconnected"
            m.bot_call_connection_id = None
            m.bot_last_event_at = datetime.now(UTC)
            await repo.upsert(m)
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


class SetGoalRequest(BaseModel):
    goal: str = Field(..., min_length=1, max_length=500)
    mode: MeetingMode | None = None


class TimekeeperAlertInput(BaseModel):
    """Settings 編集時にクライアントが送る alert 形式 (id は server 側で振る)。"""

    id: str | None = None
    minutes_from_start: int = Field(..., ge=1, le=600)
    message: str = Field(..., min_length=1, max_length=300)
    enabled: bool = True


class UpdateSettingsRequest(BaseModel):
    """会議の追加設定を編集する。指定された field のみ反映、他は維持。"""

    facilitator_name: str | None = None
    steering_enabled: bool | None = None
    timekeeper_alerts: list[TimekeeperAlertInput] | None = None


@router.patch("/{meeting_id}/settings", response_model=Meeting)
async def update_meeting_settings(
    meeting_id: str,
    organizer_id: str,
    req: UpdateSettingsRequest,
    repo: MeetingRepository = Depends(get_repo),
) -> Meeting:
    """会議の追加設定 (facilitator_name / steering_enabled / timekeeper_alerts) を編集。"""
    from helmsman.models.meeting import TimekeeperAlert

    meeting = await repo.get(meeting_id, organizer_id)
    if not meeting:
        raise HTTPException(404, "meeting not found")

    if req.facilitator_name is not None:
        # 空文字なら None にする
        name = req.facilitator_name.strip()
        meeting.facilitator_name = name or None
    if req.steering_enabled is not None:
        meeting.steering_enabled = req.steering_enabled
    if req.timekeeper_alerts is not None:
        # 既存 alert は id で同期、新規は新たに振る。fired は維持。
        existing_by_id = {a.id: a for a in meeting.timekeeper_alerts}
        new_alerts: list[TimekeeperAlert] = []
        for inp in req.timekeeper_alerts:
            prev = existing_by_id.get(inp.id or "") if inp.id else None
            new_alerts.append(
                TimekeeperAlert(
                    id=inp.id or str(uuid4()),
                    minutes_from_start=inp.minutes_from_start,
                    message=inp.message,
                    enabled=inp.enabled,
                    fired=prev.fired if prev else False,
                    fired_at=prev.fired_at if prev else None,
                )
            )
        meeting.timekeeper_alerts = new_alerts

    await repo.upsert(meeting)
    return meeting


@router.post("/{meeting_id}/set-goal", response_model=Meeting)
async def set_goal(
    meeting_id: str,
    organizer_id: str,
    req: SetGoalRequest,
    repo: MeetingRepository = Depends(get_repo),
) -> Meeting:
    """会議のゴールを後から追加 (or 変更) し、即時に論点を再分解する。

    派遣時に "監視のみ" モード (ゴール空) で開始した後、議論が進んだ段階で
    「実はこれが本論だった」とゴール宣言したくなったときに使う。
    """
    meeting = await repo.get(meeting_id, organizer_id)
    if not meeting:
        raise HTTPException(404, "meeting not found")
    if req.mode is not None:
        meeting.mode = req.mode
    meeting.goal = req.goal

    # 添付文書があれば RAG も使って分解 (group 文書も含む)
    doc_excerpts = ""
    if meeting.document_ids or meeting.group_id:
        try:
            doc_excerpts = await retrieve_excerpts_for_goal(
                meeting_id=meeting_id,
                goal=req.goal,
                repo=DocumentRepository(),
                usage_sink=meeting.usage,
                group_id=meeting.group_id,
            )
        except Exception as e:  # noqa: BLE001
            logger.warning("set_goal.excerpts_failed", error=str(e))

    decomposer = GoalDecomposer()
    try:
        meeting.topics = await decomposer.run(
            req.goal, meeting.mode, document_excerpts=doc_excerpts or None
        )
    except Exception as e:  # noqa: BLE001
        logger.error(
            "set_goal.decomposer_failed",
            meeting_id=meeting_id,
            error=str(e),
        )
        meeting.topics = []
    _accumulate_usage(meeting.usage, [decomposer])
    await repo.upsert(meeting)
    return meeting


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
        group_id=meeting.group_id,
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
    memory = MemoryRetriever()
    tone = ToneAgent()

    # 文書 RAG: 文書付き会議 or グループ所属会議だと CoverageTracker に excerpt を流す
    doc_excerpts: str | None = None
    if meeting.document_ids or meeting.group_id:
        try:
            doc_excerpts = await fetch_document_excerpts_simple(
                meeting_id=meeting_id,
                repo=DocumentRepository(),
                group_id=meeting.group_id,
            ) or None
        except Exception as e:  # noqa: BLE001
            logger.warning("tick.doc_excerpts_failed", error=str(e))

    # 全 agent を並列実行。1 つが失敗しても他は続行 (return_exceptions=True)。
    # MemoryRetriever は usage_sink を直接渡す (embed コスト集計のため)
    results = await asyncio.gather(
        coverage.run(req.recent_utterances, meeting.topics, document_excerpts=doc_excerpts),
        steering.run(meeting, req.recent_utterances, meeting.topics),
        decision_capture.run(
            meeting, req.recent_utterances, meeting.topics, document_excerpts=doc_excerpts
        ),
        quiet.run(meeting, req.participants, meeting.topics),
        dissent.run(meeting, req.recent_utterances),
        memory.run(meeting, req.recent_utterances, usage_sink=meeting.usage),
        tone.run(meeting, req.recent_utterances, participants=req.participants),
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
    memory_cand = _ok(results[5])
    tone_cand = _ok(results[6])

    meeting.topics = updated_topics
    decision_topic, decision_cand = decision_result

    # Phase 7: DecisionCapture が高 confidence で DECIDED にした topic を
    # write-through で Cosmos + AI Search に保存する (decision_persist.py)
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
                "tick.decision_persist_failed", error=str(e),
                topic_id=decision_topic.id,
            )

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
    if memory_cand:
        candidates.append(memory_cand)
    if tone_cand:
        candidates.append(tone_cand)

    # TimeKeeper (rule-based)
    tk = TimeKeeper().run(meeting)
    if tk:
        candidates.append(tk)

    # LLM 呼び出しの usage を Meeting に積み上げる
    _accumulate_usage(
        meeting.usage,
        [coverage, steering, decision_capture, quiet, dissent, memory, tone],
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
        # Phase 7: MemoryRetriever が配信された場合、その過去 decision id を
        # surfaced リストに追加して同一会議内の重複表示を抑制 (ADR-103)
        if (
            delivery.agent == "MemoryRetriever"
            and delivery.evidence_quote
            and delivery.evidence_quote not in meeting.surfaced_decision_ids
        ):
            meeting.surfaced_decision_ids.append(delivery.evidence_quote)
            # 最新 50 件のみ保持
            meeting.surfaced_decision_ids = meeting.surfaced_decision_ids[-50:]

    await repo.upsert(meeting)

    return TickResponse(
        meeting=meeting,
        candidates=candidates,
        delivery=delivery,
    )


def get_report_repo() -> MeetingReportRepository:
    return MeetingReportRepository()


@router.post(
    "/{meeting_id}/report",
    response_model=GenerateReportResponse,
)
async def generate_report(
    meeting_id: str,
    organizer_id: str,
    req: GenerateReportRequest,
    repo: MeetingRepository = Depends(get_repo),
    report_repo: MeetingReportRepository = Depends(get_report_repo),
) -> GenerateReportResponse:
    """会議終了後レポートを生成し、Cosmos meeting_reports に永続化する。

    - template があれば章立て・トーンを縛る
    - memo があれば最優先情報源として扱う (Helmsman の構造化結果より優先)
    - utterances が渡されれば引用の粒度が上がる (任意)

    1 会議で複数回呼ぶと履歴として全て残る。最新は GET /reports/latest で取れる。
    """
    meeting = await repo.get(meeting_id, organizer_id)
    if not meeting:
        raise HTTPException(404, "meeting not found")

    # utterances の優先順位:
    # 1) リクエストで明示的に渡された utterances
    # 2) 会議に永続化された transcript (bot 経由会議の発言ログ)
    # どちらも空ならレポートは meeting メタデータ (topics / decisions) のみで生成。
    utterances = req.utterances or meeting.transcript or None

    generator = MeetingReportGenerator()
    report_md = await generator.run(
        meeting,
        template=req.template,
        memo=req.memo,
        utterances=utterances,
    )

    # コスト集計に積み上げ
    _accumulate_usage(meeting.usage, [generator])
    await repo.upsert(meeting)

    report = MeetingReport(
        meeting_id=meeting.id,
        organizer_id=organizer_id,
        report_markdown=report_md,
        template_used=bool(req.template and req.template.strip()),
        memo_used=bool(req.memo and req.memo.strip()),
        utterances_included=len(utterances or []),
        template_snapshot=req.template,
        memo_snapshot=req.memo,
        generator_model=generator.deployment,
        usage=generator.last_usage,
    )
    await report_repo.create(report)

    return GenerateReportResponse(
        id=report.id,
        meeting_id=meeting.id,
        report_markdown=report_md,
        generated_at=report.generated_at,
        template_used=report.template_used,
        memo_used=report.memo_used,
        utterances_included=report.utterances_included,
    )


@router.get(
    "/{meeting_id}/reports",
    response_model=list[MeetingReport],
)
async def list_reports(
    meeting_id: str,
    organizer_id: str,
    limit: int = 20,
    repo: MeetingRepository = Depends(get_repo),
    report_repo: MeetingReportRepository = Depends(get_report_repo),
) -> list[MeetingReport]:
    """会議に紐付くレポート履歴を新しい順に返す。"""
    meeting = await repo.get(meeting_id, organizer_id)
    if not meeting:
        raise HTTPException(404, "meeting not found")
    return await report_repo.list_by_meeting(meeting_id, limit=limit)


@router.get(
    "/{meeting_id}/reports/latest",
    response_model=MeetingReport,
)
async def get_latest_report(
    meeting_id: str,
    organizer_id: str,
    repo: MeetingRepository = Depends(get_repo),
    report_repo: MeetingReportRepository = Depends(get_report_repo),
) -> MeetingReport:
    """最新レポート 1 件を返す。無ければ 404。"""
    meeting = await repo.get(meeting_id, organizer_id)
    if not meeting:
        raise HTTPException(404, "meeting not found")
    latest = await report_repo.latest(meeting_id)
    if latest is None:
        raise HTTPException(404, "no report generated yet")
    return latest
