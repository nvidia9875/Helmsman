"""Azure OpenAI client factory.

Helmsman は 2 種類のデプロイメントを使い分ける:
- HIGH (gpt-5.4)      : 高品質推論 (Goal Decomposer / Decision Capture / Dissent Surface)
- MINI (gpt-5.4-mini) : 高頻度・低レイテンシ (Coverage Tracker / Time Keeper / Steering / Quiet / Arbiter)
- REALTIME            : 音声リアルタイム介入 (L3 Speak) — 別接続が必要なため将来分
"""
from __future__ import annotations

from enum import Enum
from functools import lru_cache

from openai import AsyncAzureOpenAI

from helmsman.core.config import get_settings


class ModelTier(str, Enum):
    """LLM のティア。Agent はこれを宣言するだけで client を取得できる。"""

    HIGH = "high"
    MINI = "mini"
    REALTIME = "realtime"


@lru_cache(maxsize=1)
def _client() -> AsyncAzureOpenAI:
    """非同期 AOAI クライアントのシングルトン。"""
    settings = get_settings()
    return AsyncAzureOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
        api_version=settings.azure_openai_api_version,
    )


def get_client() -> AsyncAzureOpenAI:
    """AsyncAzureOpenAI client を返す。"""
    return _client()


def get_deployment(tier: ModelTier) -> str:
    """ティアに対応するデプロイメント名を返す。"""
    settings = get_settings()
    return {
        ModelTier.HIGH: settings.azure_openai_deployment_high,
        ModelTier.MINI: settings.azure_openai_deployment_mini,
        ModelTier.REALTIME: settings.azure_openai_deployment_realtime,
    }[tier]
