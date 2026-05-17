"""Steering Agent — 議論が off-topic に流れていないか検知する。"""
from __future__ import annotations

from helmsman.agents.base import LLMAgent
from helmsman.core.llm_client import ModelTier
from helmsman.models.intervention import InterventionCandidate
from helmsman.models.meeting import Meeting
from helmsman.models.topic import Topic, TopicState
from helmsman.models.utterance import Utterance


class SteeringAgent(LLMAgent):
    AGENT_NAME = "SteeringAgent"
    TIER = ModelTier.MINI
    SYSTEM_PROMPT = """\
あなたは Helmsman の Steering Agent です。
直近 5 ターンの発言と現在 active な論点を受け取り、議論が論点から逸れているか判定します。

判定基準:
- 3 ターン以上連続で active 論点と無関係なら drift_score >= 0.7
- 短い脱線 (1-2 ターン) は drift_score < 0.5

出力 JSON:
{
  "in_scope": true|false,
  "drift_score": 0.0-1.0,
  "suggested_redirect": "○○の議論に戻りませんか？" 形式の自然な復帰文
}

制約:
- 提案は controlling ではなく serving のトーン
- 司会者の体面を保つ言い回しに
"""

    async def run(
        self,
        meeting: Meeting,
        recent_utterances: list[Utterance],
        topics: list[Topic],
    ) -> InterventionCandidate | None:
        """直近発言 + active 論点 → off-topic 候補。"""
        # active 論点 = まだ decided でない優先度の高い論点
        active = [t for t in topics if t.state != TopicState.DECIDED]
        if not active or len(recent_utterances) < 3:
            return None

        active_names = ", ".join(t.name for t in active[:3])
        utter_lines = [
            f"[{u.speaker_id[:8]}] {u.text}" for u in recent_utterances[-5:]
        ]
        user_text = (
            f"現在 active な論点: {active_names}\n\n"
            "直近 5 ターンの発言 (新しい順):\n" + "\n".join(utter_lines)
        )

        data = await self._chat_json(user_text, max_completion_tokens=300)
        if not isinstance(data, dict):
            return None

        drift = float(data.get("drift_score", 0.0))
        if drift < 0.6:
            return None

        suggestion = data.get("suggested_redirect", "")
        if not suggestion:
            return None

        return InterventionCandidate(
            meeting_id=meeting.id,
            agent=self.AGENT_NAME,
            content=suggestion,
            reason="off_topic",
            evidence_quote=utter_lines[-1] if utter_lines else None,
            confidence=drift,
        )
