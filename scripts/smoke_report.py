"""MeetingReportGenerator の本番 smoke 検証。

3 通りで実行:
  1. テンプレも memo も無し → デフォルト構成
  2. テンプレあり + memo 無し → テンプレ章立てに従う
  3. テンプレあり + memo あり → memo を最優先情報源として取り込む

実行:
  uv run python scripts/smoke_report.py
"""
from __future__ import annotations

import asyncio
import time
from datetime import UTC, datetime

from helmsman.agents import MeetingReportGenerator
from helmsman.models.intervention import InterventionDelivery, InterventionLevel
from helmsman.models.meeting import Meeting, MeetingMode, MeetingState
from helmsman.models.topic import Topic, TopicPriority, TopicState

MEETING = Meeting(
    id="m-smoke",
    organizer_id="org-1",
    goal="Q3 マーケティング戦略の優先順位を確定する",
    mode=MeetingMode.DECISION,
    total_minutes=60,
    state=MeetingState.CONCLUDED,
    started_at=datetime(2026, 5, 21, 10, 0, tzinfo=UTC),
    ended_at=datetime(2026, 5, 21, 11, 0, tzinfo=UTC),
    topics=[
        Topic(
            name="3H 配分の確定",
            decision_criteria="Hero/Hub/Help の投資割合が決まる",
            time_budget_pct=30,
            priority=TopicPriority.CRITICAL,
            state=TopicState.DECIDED,
            evidence_quote="(0:18:42) 山田: Hero 50 / Hub 30 / Help 20 で行きましょう",
            document_reference="戦略 Memo §3H コンテンツ戦略",
            key_speakers=["yamada"],
        ),
        Topic(
            name="制作リソース",
            decision_criteria="月間制作キャパが決まる",
            time_budget_pct=25,
            priority=TopicPriority.IMPORTANT,
            state=TopicState.DECIDED,
            evidence_quote="(0:32:15) 田中: 月 30 本まで外注でスケールします",
            document_reference="戦略 Memo §制作リソース",
            key_speakers=["tanaka"],
        ),
        Topic(
            name="KPI 設計",
            decision_criteria="主目標が単一指標で決まる",
            time_budget_pct=25,
            priority=TopicPriority.CRITICAL,
            state=TopicState.DISCUSSING,
            evidence_quote=None,
            document_reference="戦略 Memo §KPI と継続観察",
        ),
        Topic(
            name="商談導線",
            decision_criteria="Hero / Hub の動画末尾 CTA が決まる",
            time_budget_pct=20,
            priority=TopicPriority.IMPORTANT,
            state=TopicState.DEEP_DIVE,
            evidence_quote=None,
        ),
    ],
    delivered_interventions=[
        InterventionDelivery(
            meeting_id="m-smoke",
            candidate_id="c-1",
            agent="DecisionCapture",
            content="3H 配分が決定として記録されました",
            reason="明示的合意",
            evidence_quote="Hero 50 / Hub 30 / Help 20 で行きましょう",
            level=InterventionLevel.L2,
            audience=["all"],
        ),
        InterventionDelivery(
            meeting_id="m-smoke",
            candidate_id="c-2",
            agent="DissentSurface",
            content="他に検討すべき視点はありますか?",
            reason="同意連鎖 5 件検出",
            evidence_quote=None,
            level=InterventionLevel.L2,
            audience=["all"],
        ),
    ],
)

TEMPLATE = """\
# Q3 マーケ定例 議事録

## 開催情報
- 日時:
- 出席:

## 決定事項
{{decisions}}

## 持ち越し論点
{{open_items}}

## 次回までの宿題
{{action_items}}
"""

MEMO = """\
山田 CTO の発言通り 3H は確定。ただし KPI は議論不十分のまま終わった印象。
個人的には「平均視聴時間」を主目標にすべきと考えるが、本日は再生回数派と
拮抗していて結論先送り。次回までに事例 3 件持ち寄り。
"""


async def run_case(label: str, **kwargs) -> None:
    print(f"\n{'=' * 60}\n[{label}]\n{'=' * 60}")
    agent = MeetingReportGenerator()
    t0 = time.perf_counter()
    report = await agent.run(MEETING, **kwargs)
    latency_ms = (time.perf_counter() - t0) * 1000
    usage = agent.last_usage
    print(report)
    print(
        f"\n--- latency: {latency_ms:.0f} ms | "
        f"prompt={usage.prompt_tokens if usage else 0} / "
        f"completion={usage.completion_tokens if usage else 0} ---"
    )


async def main() -> int:
    await run_case("Case 1: default (no template, no memo)")
    await run_case("Case 2: with template only", template=TEMPLATE)
    await run_case("Case 3: template + memo", template=TEMPLATE, memo=MEMO)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
