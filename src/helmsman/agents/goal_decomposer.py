"""Goal Decomposer — 会議のゴールを論点 list に分解する。"""
from __future__ import annotations

from helmsman.agents.base import LLMAgent
from helmsman.core.llm_client import ModelTier
from helmsman.models.meeting import MeetingMode
from helmsman.models.topic import Topic, TopicPriority


class GoalDecomposer(LLMAgent):
    AGENT_NAME = "GoalDecomposer"
    TIER = ModelTier.HIGH
    SYSTEM_PROMPT = """\
あなたは Helmsman の Goal Decomposer Agent です。
会議のゴール文を受け取り、ゴール達成に必要な論点 3-7 個に MECE で分解します。

各論点は以下の構造で JSON 出力してください:
{
  "topics": [
    {
      "name": "論点名 (10文字以内)",
      "decision_criteria": "決定済とみなす条件 (具体的に)",
      "time_budget_pct": <0-100 の整数>,
      "priority": "Critical" | "Important" | "Optional",
      "dependencies": ["先行する論点名のリスト (なければ空)"]
    },
    ...
  ]
}

制約:
- time_budget_pct の合計は 100 にする
- Decision モードでは Critical 論点を1つ以上含む
- 論点は MECE (重複なし、漏れなし)
- 日本特有の婉曲表現に注意 ("検討します" は決定ではない)
"""

    async def run(self, goal: str, mode: MeetingMode = MeetingMode.DECISION) -> list[Topic]:
        user_text = f"会議モード: {mode.value}\n会議のゴール: {goal}"
        data = await self._chat_json(user_text, max_completion_tokens=1200)
        topics_data = data.get("topics", []) if isinstance(data, dict) else []

        topics: list[Topic] = []
        for t in topics_data:
            try:
                priority = TopicPriority(t.get("priority", "Important"))
            except ValueError:
                priority = TopicPriority.IMPORTANT
            topics.append(
                Topic(
                    name=str(t.get("name", ""))[:32],
                    decision_criteria=str(t.get("decision_criteria", "")),
                    time_budget_pct=float(t.get("time_budget_pct", 0)),
                    priority=priority,
                    dependencies=list(t.get("dependencies", [])),
                )
            )
        self.log.info("decomposed", count=len(topics), mode=mode.value)
        return topics
