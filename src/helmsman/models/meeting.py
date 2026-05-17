"""Meeting — 会議全体の状態オブジェクト。"""
from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field

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

    @property
    def time_remaining_pct(self) -> float:
        """残時間割合 (0.0-1.0)。"""
        if not self.started_at:
            return 1.0
        elapsed = (datetime.now(UTC) - self.started_at).total_seconds() / 60.0
        return max(0.0, min(1.0, 1.0 - elapsed / max(1, self.total_minutes)))
