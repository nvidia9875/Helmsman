"""LLM usage tracking models.

各 Agent の LLM 呼び出しから token / cost を回収して
Meeting 単位に集計するためのデータ型。
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class UsageRecord(BaseModel):
    """LLM 呼び出し 1 回ぶんの token usage。Agent から tick へ渡す sidecar。"""

    agent_name: str
    model_deployment: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class AgentUsageRollup(BaseModel):
    """1 会議内で agent 単位に積み上げた usage。"""

    agent_name: str
    model_deployment: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    call_count: int = 0


class MeetingUsage(BaseModel):
    """1 会議の usage 全体。Meeting に埋め込んで Cosmos に永続化する。"""

    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    call_count: int = 0
    by_agent: dict[str, AgentUsageRollup] = Field(default_factory=dict)

    def apply(self, record: UsageRecord, cost_usd: float) -> None:
        """新しい UsageRecord を集計に加える (in-place 更新)。

        Cosmos 上の Meeting ドキュメントを upsert する直前に呼ぶ想定。
        """
        bucket = self.by_agent.get(record.agent_name)
        if bucket is None:
            bucket = AgentUsageRollup(
                agent_name=record.agent_name,
                model_deployment=record.model_deployment,
            )
            self.by_agent[record.agent_name] = bucket

        bucket.prompt_tokens += record.prompt_tokens
        bucket.completion_tokens += record.completion_tokens
        bucket.total_tokens += record.total_tokens
        bucket.cost_usd += cost_usd
        bucket.call_count += 1

        self.total_prompt_tokens += record.prompt_tokens
        self.total_completion_tokens += record.completion_tokens
        self.total_tokens += record.total_tokens
        self.total_cost_usd += cost_usd
        self.call_count += 1
