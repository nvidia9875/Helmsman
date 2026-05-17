"""Azure OpenAI 料金表 (USD / 1M tokens)。

⚠️ 価格は変動する。最新値は
https://azure.microsoft.com/en-us/pricing/details/cognitive-services/openai-service/
を参照して PRICING_TABLE を更新すること。

最終確認: 2026-05-17。Helmsman の代表的なデプロイメント名 (gpt-5.4 / gpt-5.4-mini /
gpt-realtime-1.5) は社内呼称であり、実体は GPT-4o / GPT-4o-mini / gpt-4o-realtime の
価格に準拠している。未登録のモデルは _FALLBACK_PRICE にフォールバックする。
"""
from __future__ import annotations

from helmsman.core.usage import UsageRecord


class ModelPrice:
    """1M tokens あたり USD 単価 (input / output)。"""

    __slots__ = ("input_per_million", "output_per_million")

    def __init__(self, input_per_million: float, output_per_million: float) -> None:
        self.input_per_million = input_per_million
        self.output_per_million = output_per_million


# デプロイメント名 → 価格。Settings の azure_openai_deployment_* と揃える。
PRICING_TABLE: dict[str, ModelPrice] = {
    "gpt-5.4": ModelPrice(input_per_million=2.50, output_per_million=10.00),
    "gpt-5.4-mini": ModelPrice(input_per_million=0.15, output_per_million=0.60),
    # text in/out 単価 (audio は別途。L3 実装時に分岐させる)
    "gpt-realtime-1.5": ModelPrice(input_per_million=5.00, output_per_million=20.00),
}

# 未登録デプロイメントが来た時の保守的な見積もり (HIGH と同じ)
_FALLBACK_PRICE = ModelPrice(input_per_million=2.50, output_per_million=10.00)


def get_price(deployment: str) -> ModelPrice:
    """デプロイメント名から価格を引く。未知のものは FALLBACK。"""
    return PRICING_TABLE.get(deployment, _FALLBACK_PRICE)


def calculate_cost_usd(record: UsageRecord) -> float:
    """1 呼び出しぶんの USD 単価を計算する。"""
    price = get_price(record.model_deployment)
    input_cost = (record.prompt_tokens / 1_000_000) * price.input_per_million
    output_cost = (record.completion_tokens / 1_000_000) * price.output_per_million
    return input_cost + output_cost
