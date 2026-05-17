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
- 「前回からの引き継ぎ事項」が与えられた場合、その未解決論点を継続するか
  発展形に変形して必ず 1 件以上含める (時間配分は新規論点とバランスを取る)
- 「参考文書」が与えられた場合、その内容に基づいた論点・決定基準を盛り込む
  (文書を引用する形で具体性を上げる)
"""

    async def run(
        self,
        goal: str,
        mode: MeetingMode = MeetingMode.DECISION,
        inherited_topics: list[Topic] | None = None,
        document_excerpts: str | None = None,
    ) -> list[Topic]:
        """ゴールを論点に分解する。

        Args:
            goal: 会議ゴール文
            mode: 会議モード
            inherited_topics: 前回会議からの未解決論点 (継続会議の場合のみ)。
                              system prompt に「引き継ぎ事項」セクションとして注入される。
            document_excerpts: RAG で取得した参考文書の抜粋テキスト。空文字や None は
                               スキップ。投入時はトークン消費するので呼び出し側で
                               長さを制御すること。
        """
        sections = [f"会議モード: {mode.value}", f"会議のゴール: {goal}"]
        if inherited_topics:
            inherited_lines = [
                f"- {t.name} (前回状態: {t.state.value}, 基準: {t.decision_criteria})"
                for t in inherited_topics
            ]
            sections.append(
                "前回からの引き継ぎ事項 (未解決):\n" + "\n".join(inherited_lines)
            )
        if document_excerpts:
            sections.append("参考文書 (抜粋):\n" + document_excerpts)
        user_text = "\n\n".join(sections)
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
