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
参考文書が与えられた場合は、発言と文書内容を結び付けて document_reference を埋めます。

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
      "confidence": 0.0-1.0,
      "document_reference": "参考文書 X §3 採用要件 (関連する場合のみ、なければ null)"
    }
  ],
  "off_topic_score": 0.0-1.0
}

制約:
- 確信が低い (<0.7) ものは confidence を低くする
- 発言から論点に semantic match できない場合は state 変更しない
- document_reference は参考文書内の特定箇所と明確に紐付くときだけ埋める (推測しない)
"""

    async def run(
        self,
        recent_utterances: list[Utterance],
        topics: list[Topic],
        document_excerpts: str | None = None,
    ) -> list[Topic]:
        """発言ストリーム + topics + (任意で参考文書) → 更新済み topics リスト。"""
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
        sections = [
            "現在の論点:\n" + "\n".join(topic_lines),
            "直近の発言 (新しい順):\n" + "\n".join(utter_lines),
        ]
        if document_excerpts:
            sections.append("参考文書 (抜粋):\n" + document_excerpts)
        user_text = "\n\n".join(sections)

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
            # 文書参照 (RAG で取れたときだけ)
            doc_ref = u.get("document_reference")
            if doc_ref:
                topic.document_reference = str(doc_ref).strip() or None

        self.log.debug("coverage.updated", updated=len(updates))
        return topics
