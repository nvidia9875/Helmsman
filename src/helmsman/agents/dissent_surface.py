"""Dissent Surface — 押し殺された反対意見を匿名で表面化する。"""
from __future__ import annotations

from helmsman.agents.base import LLMAgent
from helmsman.core.llm_client import ModelTier
from helmsman.models.intervention import InterventionCandidate
from helmsman.models.meeting import Meeting
from helmsman.models.utterance import Utterance


class DissentSurface(LLMAgent):
    AGENT_NAME = "DissentSurface"
    TIER = ModelTier.HIGH  # 微妙な検知なので精度重視
    SYSTEM_PROMPT = """\
あなたは Helmsman の Dissent Surface Agent です。
直近 10 ターンの発言を解析し、以下を検知します:

1. 「同意連鎖」: 3 回以上連続で賛成発言のみ続いている
2. 過去発言で懸念色のあった参加者が沈黙している

検知時、その懸念を匿名 (反対者を特定しない形) で表面化します。

出力 JSON:
{
  "agreement_chain_detected": true|false,
  "concerned_about": "想定される懸念点 (発言から推論)",
  "surface_card": "念のため、○○について懸念点はありませんか？ 形式の文",
  "confidence": 0.0-1.0
}

制約:
- 反対者を名指ししない (心理的安全性のため)
- 権威勾配 (上司発言中) では発火しない (Arbiter 側でも制御)
"""

    async def run(
        self, meeting: Meeting, recent_utterances: list[Utterance]
    ) -> InterventionCandidate | None:
        if len(recent_utterances) < 5:
            return None

        utter_lines = [
            f"[{u.speaker_id[:8]}] {u.text}" for u in recent_utterances[-10:]
        ]
        user_text = "直近の発言 (新しい順):\n" + "\n".join(utter_lines)

        data = await self._chat_json(user_text, max_completion_tokens=300)
        if not isinstance(data, dict) or not data.get("agreement_chain_detected"):
            return None

        surface = data.get("surface_card", "")
        if not surface:
            return None

        return InterventionCandidate(
            meeting_id=meeting.id,
            agent=self.AGENT_NAME,
            content=surface,
            reason="agreement_chain",
            evidence_quote=data.get("concerned_about"),
            confidence=float(data.get("confidence", 0.7)),
        )
