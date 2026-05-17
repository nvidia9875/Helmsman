"""Usage / pricing aggregation tests."""
from __future__ import annotations

import pytest

from helmsman.core.pricing import (
    PRICING_TABLE,
    calculate_cost_usd,
    get_price,
)
from helmsman.core.usage import MeetingUsage, UsageRecord


def test_calculate_cost_uses_separate_input_output_rates() -> None:
    record = UsageRecord(
        agent_name="GoalDecomposer",
        model_deployment="gpt-5.4",
        prompt_tokens=1_000_000,
        completion_tokens=1_000_000,
        total_tokens=2_000_000,
    )
    price = PRICING_TABLE["gpt-5.4"]
    expected = price.input_per_million + price.output_per_million
    assert calculate_cost_usd(record) == pytest.approx(expected)


def test_calculate_cost_unknown_deployment_falls_back() -> None:
    record = UsageRecord(
        agent_name="GoalDecomposer",
        model_deployment="phantom-future-model",
        prompt_tokens=500_000,
        completion_tokens=0,
        total_tokens=500_000,
    )
    fallback = get_price("phantom-future-model")
    expected = 0.5 * fallback.input_per_million
    assert calculate_cost_usd(record) == pytest.approx(expected)


def test_meeting_usage_apply_accumulates_per_agent_and_total() -> None:
    usage = MeetingUsage()

    r1 = UsageRecord(
        agent_name="CoverageTracker",
        model_deployment="gpt-5.4-mini",
        prompt_tokens=1000,
        completion_tokens=200,
        total_tokens=1200,
    )
    r2 = UsageRecord(
        agent_name="CoverageTracker",
        model_deployment="gpt-5.4-mini",
        prompt_tokens=800,
        completion_tokens=150,
        total_tokens=950,
    )
    r3 = UsageRecord(
        agent_name="SteeringAgent",
        model_deployment="gpt-5.4-mini",
        prompt_tokens=400,
        completion_tokens=80,
        total_tokens=480,
    )

    for record in (r1, r2, r3):
        usage.apply(record, calculate_cost_usd(record))

    # 全体
    assert usage.total_prompt_tokens == 2200
    assert usage.total_completion_tokens == 430
    assert usage.total_tokens == 2630
    assert usage.call_count == 3

    # agent 別
    coverage = usage.by_agent["CoverageTracker"]
    assert coverage.call_count == 2
    assert coverage.prompt_tokens == 1800
    assert coverage.completion_tokens == 350
    assert coverage.total_tokens == 2150

    steering = usage.by_agent["SteeringAgent"]
    assert steering.call_count == 1
    assert steering.prompt_tokens == 400

    # コストは小数だが正方向に積み上がっている
    assert usage.total_cost_usd > 0
    assert coverage.cost_usd > 0
    assert steering.cost_usd > 0
    # 全体 = 各 agent の合計
    assert usage.total_cost_usd == pytest.approx(
        coverage.cost_usd + steering.cost_usd
    )


def test_meeting_usage_starts_empty() -> None:
    usage = MeetingUsage()
    assert usage.total_tokens == 0
    assert usage.total_cost_usd == 0.0
    assert usage.call_count == 0
    assert usage.by_agent == {}


def test_known_deployments_have_pricing_entries() -> None:
    """Settings のデフォルトデプロイメント名は必ず PRICING_TABLE に存在する。

    新しいモデルを追加する時はこのテストが落ちて気付ける。
    """
    from helmsman.core.config import Settings

    expected_deployments = {
        Settings.model_fields["azure_openai_deployment_high"].default,
        Settings.model_fields["azure_openai_deployment_mini"].default,
        Settings.model_fields["azure_openai_deployment_realtime"].default,
    }
    missing = expected_deployments - PRICING_TABLE.keys()
    assert not missing, f"PRICING_TABLE missing: {missing}"
