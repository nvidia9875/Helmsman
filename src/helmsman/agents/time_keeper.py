"""Time Keeper — 時間予算とカバレッジ進捗の差分を監視する (rule-based)。"""
from __future__ import annotations

from helmsman.core.llm_client import ModelTier
from helmsman.core.logging import logger
from helmsman.models.intervention import InterventionCandidate
from helmsman.models.meeting import Meeting
from helmsman.models.topic import TopicState


class TimeKeeper:
    """時間管理。LLM 不要、ルールベースで高速。"""

    AGENT_NAME = "TimeKeeper"
    TIER = ModelTier.MINI

    def __init__(self) -> None:
        self.log = logger.bind(agent=self.AGENT_NAME)

    def run(self, meeting: Meeting) -> InterventionCandidate | None:
        """残時間 + カバレッジ から警告候補を生成。"""
        time_left_pct = meeting.time_remaining_pct
        if time_left_pct <= 0:
            return None

        not_started = [t for t in meeting.topics if t.state == TopicState.NOT_STARTED]
        critical_unfinished = [
            t for t in not_started if t.priority.value == "Critical"
        ]

        # 警告条件 1: 残時間 < 30% かつ未着手 Critical あり
        if time_left_pct < 0.30 and critical_unfinished:
            names = ", ".join(t.name for t in critical_unfinished)
            return InterventionCandidate(
                meeting_id=meeting.id,
                agent=self.AGENT_NAME,
                content=(
                    f"残り {int(time_left_pct * 100)}% で重要論点 "
                    f"{len(critical_unfinished)} つが未着手です: {names}"
                ),
                reason="critical_unfinished",
                confidence=0.95,
            )

        # 警告条件 2: 残時間 < 20% かつ任意の論点が未着手
        if time_left_pct < 0.20 and not_started:
            names = ", ".join(t.name for t in not_started[:3])
            return InterventionCandidate(
                meeting_id=meeting.id,
                agent=self.AGENT_NAME,
                content=f"残り時間わずか。未着手論点 {len(not_started)} つ: {names}",
                reason="time_almost_up",
                confidence=0.90,
            )

        return None
