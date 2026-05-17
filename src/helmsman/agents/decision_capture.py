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
参考文書 (社内ポリシー / 過去の合意事項 / 仕様書) が与えられた場合は、
今回の決定が文書と矛盾していないか必ずチェックしてください。

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
  "dissent": ["反対者の名前リスト (もしあれば)"],
  "contradiction_warning": "参考文書 X §3 と矛盾: 文書では...と書かれている (該当しなければ null)",
  "contradicted_document": "矛盾源となる文書のファイル名 (該当しなければ null)"
}

contradiction_warning は明確かつ具体的な矛盾だけ報告してください (推測で警告を出さない)。
"""

    async def run(
        self,
        meeting: Meeting,
        recent_utterances: list[Utterance],
        topics: list[Topic],
        document_excerpts: str | None = None,
    ) -> tuple[Topic | None, InterventionCandidate | None]:
        """発言 → 決定検知。topic 状態更新 + 確認介入候補。

        document_excerpts が与えられた場合、決定が文書と矛盾していたら
        intervention content に ⚠️ プレフィックスを付けて confidence を維持。
        """
        if len(recent_utterances) < 2:
            return None, None

        topic_names = ", ".join(t.name for t in topics if t.state != TopicState.DECIDED)
        if not topic_names:
            return None, None

        utter_lines = [
            f"[{u.speaker_id[:8]}] {u.text}" for u in recent_utterances[-10:]
        ]
        sections = [
            f"現在の未決定論点: {topic_names}",
            "直近の発言 (新しい順):\n" + "\n".join(utter_lines),
        ]
        if document_excerpts:
            sections.append("参考文書 (抜粋):\n" + document_excerpts)
        user_text = "\n\n".join(sections)

        data = await self._chat_json(user_text, max_completion_tokens=600)
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
        warning = (data.get("contradiction_warning") or "").strip() or None
        contradicted_doc = (data.get("contradicted_document") or "").strip() or None

        # 高 confidence なら状態を decided に
        if confidence >= 0.7:
            target.state = TopicState.DECIDED
            target.last_mention_at = datetime.now(UTC)
            target.evidence_quote = decision

        # 介入内容: 矛盾検出時は ⚠️ プレフィックス
        content = f"決定: {decision} (担当: {owner}, 期日: {deadline})"
        reason = "decision_captured"
        if warning:
            content = f"⚠️ 文書と矛盾の可能性: {warning}\n決定: {decision}"
            reason = "decision_contradiction"
            self.log.warning(
                "decision.contradiction",
                document=contradicted_doc,
                warning=warning[:200],
                decision=decision[:80],
            )

        candidate = InterventionCandidate(
            meeting_id=meeting.id,
            agent=self.AGENT_NAME,
            content=content,
            reason=reason,
            evidence_quote=utter_lines[-1] if utter_lines else None,
            confidence=confidence,
        )
        return target, candidate
