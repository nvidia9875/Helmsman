"""Meeting — 会議全体の状態オブジェクト。"""
from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field

from helmsman.core.usage import MeetingUsage
from helmsman.models.intervention import InterventionDelivery
from helmsman.models.topic import Topic


class MeetingMode(str, Enum):
    """会議モード。エージェントの優先度・閾値が動的に変わる。"""

    DECISION = "Decision"
    BRAINSTORM = "Brainstorm"
    STATUS = "Status"
    INTERVIEW = "Interview"
    ONE_ON_ONE = "1on1"
    KICKOFF = "Kickoff"


class MeetingState(str, Enum):
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    CONCLUDED = "concluded"


class UserIntensity(str, Enum):
    """ユーザーが設定する介入頻度。"""

    QUIET = "quiet"
    NORMAL = "normal"
    AGGRESSIVE = "aggressive"


class Meeting(BaseModel):
    """会議エンティティ。Cosmos の `meetings` コンテナに格納される。"""

    id: str = Field(default_factory=lambda: str(uuid4()))
    organizer_id: str
    goal: str
    mode: MeetingMode = MeetingMode.DECISION
    total_minutes: int = 60
    state: MeetingState = MeetingState.SCHEDULED
    user_intensity: UserIntensity = UserIntensity.NORMAL

    started_at: datetime | None = None
    ended_at: datetime | None = None

    topics: list[Topic] = Field(default_factory=list)
    participant_ids: list[str] = Field(default_factory=list)
    last_intervention_at: datetime | None = None
    recent_utterance_density: float = 0.0  # 0-1, Arbiter が参照

    # ----- 会議継続性 (シリーズ / 引き継ぎ) -----
    parent_meeting_id: str | None = None  # 直前の会議 ID
    series_id: str | None = None          # 同シリーズ会議 (定例) を束ねる ID
    series_index: int | None = None       # シリーズ内何回目か (1-origin)
    inherited_topic_ids: list[str] = Field(default_factory=list)  # 引き継いだ論点 ID

    # ----- 文書グラウンディング -----
    document_ids: list[str] = Field(default_factory=list)  # 紐付く文書 ID
    document_index_name: str | None = None  # Azure AI Search / Cosmos Vector のインデックス名

    # ----- LLM usage / コスト集計 -----
    usage: MeetingUsage = Field(default_factory=MeetingUsage)

    # ----- Teams Bot 連携 (ACS Call Automation) -----
    teams_meeting_url: str | None = None
    bot_call_connection_id: str | None = None
    bot_status: str = "idle"  # idle / connecting / in_call / disconnected / failed
    bot_last_event_at: datetime | None = None

    # ----- Intervention 履歴 (Frontend が feed として表示) -----
    delivered_interventions: list[InterventionDelivery] = Field(default_factory=list)

    @property
    def time_remaining_pct(self) -> float:
        """残時間割合 (0.0-1.0)。"""
        if not self.started_at:
            return 1.0
        elapsed = (datetime.now(UTC) - self.started_at).total_seconds() / 60.0
        return max(0.0, min(1.0, 1.0 - elapsed / max(1, self.total_minutes)))
