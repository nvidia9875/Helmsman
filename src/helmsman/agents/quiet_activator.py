"""Quiet Activator — 発言の少ない参加者を自然に促す。"""
from __future__ import annotations

import statistics

from helmsman.agents.base import LLMAgent
from helmsman.core.llm_client import ModelTier
from helmsman.models.intervention import InterventionCandidate
from helmsman.models.meeting import Meeting
from helmsman.models.participant import Participant
from helmsman.models.topic import Topic, TopicState


class QuietActivator(LLMAgent):
    AGENT_NAME = "QuietActivator"
    TIER = ModelTier.MINI
    SYSTEM_PROMPT = """\
あなたは Helmsman の Quiet Activator Agent です。
発言時間が著しく少ない参加者に対し、その人が貢献できそうな論点で発言を促します。

文化的配慮:
- 高コンテクスト文化 (日本) では「○○さんはどう思われますか？」と丁寧に
- 圧をかけず opt-in できる言い回しに
- 名指しが不適切な場合は「他にご意見ある方は？」と全体に

出力 JSON:
{
  "invitation": "○○さん、△△の観点はいかがですか？",
  "target_speaker": "対象者の名前",
  "confidence": 0.0-1.0
}
"""

    async def run(
        self,
        meeting: Meeting,
        participants: list[Participant],
        topics: list[Topic],
        min_meeting_minutes: int = 20,
    ) -> InterventionCandidate | None:
        """参加者統計 → 沈黙者活性化候補。"""
        # 短い会議では発火しない
        if meeting.total_minutes < min_meeting_minutes:
            return None

        # 参加者が 3 名以下なら自然と全員話すので発火しない
        if len(participants) < 3:
            return None

        speak_secs = [p.total_speak_seconds for p in participants]
        mean = statistics.mean(speak_secs)
        stdev = statistics.stdev(speak_secs) if len(speak_secs) > 1 else 0
        if stdev == 0:
            return None

        # z-score < -1.5 の参加者を抽出
        candidates = [
            p
            for p, s in zip(participants, speak_secs, strict=True)
            if (s - mean) / stdev < -1.5
        ]
        if not candidates:
            return None

        target = candidates[0]
        active_topic = next(
            (t for t in topics if t.state == TopicState.DISCUSSING),
            topics[0] if topics else None,
        )
        topic_name = active_topic.name if active_topic else ""

        user_text = (
            f"沈黙が気になる参加者: {target.display_name}\n"
            f"現在の論点: {topic_name}\n"
            f"発話時間: {target.total_speak_seconds:.0f}秒 (平均 {mean:.0f}秒)"
        )

        data = await self._chat_json(user_text, max_completion_tokens=200)
        if not isinstance(data, dict):
            return None

        invitation = data.get("invitation", "")
        if not invitation:
            return None

        return InterventionCandidate(
            meeting_id=meeting.id,
            agent=self.AGENT_NAME,
            content=invitation,
            reason="quiet_participant",
            confidence=float(data.get("confidence", 0.7)),
        )
