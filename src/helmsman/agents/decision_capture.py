"""Decision Capture — 決定の検知と構造化。"""
from __future__ import annotations

from datetime import UTC, datetime

from helmsman.agents.base import LLMAgent
from helmsman.core.llm_client import ModelTier
from helmsman.models.intervention import InterventionCandidate
from helmsman.models.meeting import Meeting
from helmsman.models.topic import Topic, TopicState
from helmsman.models.utterance import Utterance


class DecisionCapture(LLMAgent):
    AGENT_NAME = "DecisionCapture"
    TIER = ModelTier.HIGH  # 精度重要
    SYSTEM_PROMPT = """\
あなたは Helmsman の Decision Capture Agent です。
発言ストリームから「決定」を検出し構造化します。

検出シグナル:
- "では○○で行きましょう"
- "それで決まり" / "OK進めます"
- "△△さんお願いします、□□までに"

避けるべき (決定ではない):
- "検討します" (日本式の婉曲な No)
- "持ち帰ります" (保留)
- "そうですね" (単なる同意)

出力 JSON:
{
  "detected": true|false,
  "topic_name": "対象論点 (provided list から選ぶ)",
  "decision": "決定内容を簡潔に",
  "owner": "担当者の名前または発話者",
  "deadline": "期日 (YYYY-MM-DD or 自然言語)",
  "confidence": 0.0-1.0,
  "dissent": ["反対者の名前リスト (もしあれば)"]
}
"""

    async def run(
        self,
        meeting: Meeting,
        recent_utterances: list[Utterance],
        topics: list[Topic],
    ) -> tuple[Topic | None, InterventionCandidate | None]:
        """発言 → 決定検知。topic 状態更新 + 確認介入候補。"""
        if len(recent_utterances) < 2:
            return None, None

        topic_names = ", ".join(t.name for t in topics if t.state != TopicState.DECIDED)
        if not topic_names:
            return None, None

        utter_lines = [
            f"[{u.speaker_id[:8]}] {u.text}" for u in recent_utterances[-10:]
        ]
        user_text = (
            f"現在の未決定論点: {topic_names}\n\n"
            "直近の発言 (新しい順):\n" + "\n".join(utter_lines)
        )

        data = await self._chat_json(user_text, max_completion_tokens=500)
        if not isinstance(data, dict) or not data.get("detected"):
            return None, None

        topic_name = data.get("topic_name", "")
        target = next((t for t in topics if t.name == topic_name), None)
        if not target:
            return None, None

        confidence = float(data.get("confidence", 0.5))
        decision = data.get("decision", "")
        owner = data.get("owner", "")
        deadline = data.get("deadline", "")

        # 高 confidence なら状態を decided に
        if confidence >= 0.7:
            target.state = TopicState.DECIDED
            target.last_mention_at = datetime.now(UTC)
            target.evidence_quote = decision

        # 確認介入 (常に出す: 全員に "決まりました" を可視化)
        candidate = InterventionCandidate(
            meeting_id=meeting.id,
            agent=self.AGENT_NAME,
            content=f"決定: {decision} (担当: {owner}, 期日: {deadline})",
            reason="decision_captured",
            evidence_quote=utter_lines[-1] if utter_lines else None,
            confidence=confidence,
        )
        return target, candidate
