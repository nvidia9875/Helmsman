"""Coverage Tracker — 発言を論点にマッチングし状態を更新する。"""
from __future__ import annotations

from datetime import UTC, datetime

from helmsman.agents.base import LLMAgent
from helmsman.core.llm_client import ModelTier
from helmsman.models.topic import Topic, TopicState
from helmsman.models.utterance import Utterance


class CoverageTracker(LLMAgent):
    AGENT_NAME = "CoverageTracker"
    TIER = ModelTier.MINI  # 高頻度なので mini
    SYSTEM_PROMPT = """\
あなたは Helmsman の Coverage Tracker Agent です。
直近の発言ストリームと現在のトピックプランを受け取り、各論点の状態を更新します。

判定状態:
- not_started : 60秒未満の関連発言
- discussing  : 60-180秒の議論、決定なし
- deep_dive   : 180秒以上、2 視点以上探索された
- decided     : 明確な決定句あり

出力 JSON:
{
  "topic_updates": [
    {
      "topic_name": "論点名",
      "state": "discussing|deep_dive|...",
      "key_speakers": ["話者名"],
      "evidence_quote": "根拠となる発言の抜粋",
      "confidence": 0.0-1.0
    }
  ],
  "off_topic_score": 0.0-1.0
}

制約:
- 確信が低い (<0.7) ものは confidence を低くする
- 発言から論点に semantic match できない場合は state 変更しない
"""

    async def run(
        self, recent_utterances: list[Utterance], topics: list[Topic]
    ) -> list[Topic]:
        """発言ストリーム + topics → 更新済み topics リスト。"""
        if not recent_utterances or not topics:
            return topics

        # コンパクトなコンテキストを作る
        utter_lines = [
            f"[{u.speaker_id[:8]}] {u.text}" for u in recent_utterances[-15:]
        ]
        topic_lines = [
            f"- {t.name} (現在: {t.state.value}, 基準: {t.decision_criteria})"
            for t in topics
        ]
        user_text = (
            "現在の論点:\n" + "\n".join(topic_lines) + "\n\n"
            "直近の発言 (新しい順):\n" + "\n".join(utter_lines)
        )

        data = await self._chat_json(user_text, max_completion_tokens=800)
        updates = data.get("topic_updates", []) if isinstance(data, dict) else []
        now = datetime.now(UTC)

        # name -> topic でルックアップ
        by_name = {t.name: t for t in topics}
        for u in updates:
            name = u.get("topic_name", "")
            topic = by_name.get(name)
            if not topic:
                continue
            try:
                topic.state = TopicState(u.get("state", topic.state.value))
            except ValueError:
                pass
            topic.key_speakers = list(u.get("key_speakers", topic.key_speakers))
            topic.evidence_quote = u.get("evidence_quote")
            topic.confidence = float(u.get("confidence", 0.5))
            topic.last_mention_at = now

        self.log.debug("coverage.updated", updated=len(updates))
        return topics
