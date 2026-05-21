"""MeetingReportGenerator のユニットテスト。

LLM (`_chat`) はモック化し、プロンプト組み立て + 出力ハンドリングを検証する。
"""
from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from helmsman.agents import MeetingReportGenerator
from helmsman.models.intervention import (
    InterventionDelivery,
    InterventionLevel,
)
from helmsman.models.meeting import Meeting, MeetingMode, MeetingState
from helmsman.models.topic import Topic, TopicPriority, TopicState
from helmsman.models.utterance import Utterance


def _meeting() -> Meeting:
    return Meeting(
        id="m-1",
        organizer_id="org-1",
        goal="新サービスのローンチ可否を決定する",
        mode=MeetingMode.DECISION,
        total_minutes=60,
        state=MeetingState.CONCLUDED,
        started_at=datetime(2026, 5, 21, 10, 0, tzinfo=UTC),
        ended_at=datetime(2026, 5, 21, 11, 0, tzinfo=UTC),
        topics=[
            Topic(
                id="t-1",
                name="Go/NoGo 判定",
                decision_criteria="ローンチ可否が明示される",
                time_budget_pct=40,
                priority=TopicPriority.CRITICAL,
                state=TopicState.DECIDED,
                evidence_quote="(0:48:12) 山田: 9 月 15 日で Go で行きましょう",
                key_speakers=["p-yamada"],
            ),
            Topic(
                id="t-2",
                name="QA 計画",
                decision_criteria="QA 期間が確定する",
                time_budget_pct=30,
                priority=TopicPriority.IMPORTANT,
                state=TopicState.DISCUSSING,
                evidence_quote=None,
            ),
        ],
        delivered_interventions=[
            InterventionDelivery(
                meeting_id="m-1",
                candidate_id="c-1",
                agent="DecisionCapture",
                content="Go/NoGo を決定として記録しました",
                reason="明示的合意",
                evidence_quote="9 月 15 日で Go で行きましょう",
                level=InterventionLevel.L2,
                audience=["all"],
            ),
        ],
    )


@pytest.mark.asyncio
async def test_default_report_uses_template_when_none(monkeypatch):
    """テンプレもメモも無ければデフォルト構成で markdown を返す。"""
    agent = MeetingReportGenerator()
    expected = "# 会議サマリ\n## 概要\n..."
    monkeypatch.setattr(agent, "_chat", AsyncMock(return_value=expected))

    report = await agent.run(_meeting())

    assert report == expected
    # _chat に渡された user_text にコンテキスト JSON が含まれている
    call_args = agent._chat.call_args
    user_text = call_args.args[0] if call_args.args else call_args.kwargs["user_text"]
    assert "会議コンテキスト (JSON)" in user_text
    assert "新サービスのローンチ可否を決定する" in user_text
    assert "ユーザー提供テンプレート" not in user_text
    assert "ユーザー手書きメモ" not in user_text


@pytest.mark.asyncio
async def test_template_section_injected_when_provided(monkeypatch):
    """template が渡されればプロンプトに "ユーザー提供テンプレート" 章が入る。"""
    agent = MeetingReportGenerator()
    monkeypatch.setattr(agent, "_chat", AsyncMock(return_value="ok"))

    template = "# {{title}}\n## 決定\n{{decisions}}\n## TODO\n{{action_items}}"
    await agent.run(_meeting(), template=template)

    user_text = agent._chat.call_args.args[0]
    assert "ユーザー提供テンプレート" in user_text
    assert "{{decisions}}" in user_text


@pytest.mark.asyncio
async def test_memo_section_injected_and_marked_authoritative(monkeypatch):
    """memo は権威ある情報源として注入される。"""
    agent = MeetingReportGenerator()
    monkeypatch.setattr(agent, "_chat", AsyncMock(return_value="ok"))

    memo = "山田 CTO の発言は記録通りだが、私見では QA 期間を 2 週延ばすべき"
    await agent.run(_meeting(), memo=memo)

    user_text = agent._chat.call_args.args[0]
    assert "ユーザー手書きメモ" in user_text
    assert "権威ある情報源" in user_text
    assert "QA 期間を 2 週延ばすべき" in user_text


@pytest.mark.asyncio
async def test_blank_template_and_memo_treated_as_absent(monkeypatch):
    """空白だけの template / memo はセクションを追加しない。"""
    agent = MeetingReportGenerator()
    monkeypatch.setattr(agent, "_chat", AsyncMock(return_value="ok"))

    await agent.run(_meeting(), template="   \n  ", memo="")

    user_text = agent._chat.call_args.args[0]
    assert "ユーザー提供テンプレート" not in user_text
    assert "ユーザー手書きメモ" not in user_text


@pytest.mark.asyncio
async def test_utterances_truncated_when_over_limit(monkeypatch):
    """発言が大量なら先頭+末尾を残して圧縮される。"""
    agent = MeetingReportGenerator()
    monkeypatch.setattr(agent, "_chat", AsyncMock(return_value="ok"))

    now = datetime(2026, 5, 21, 10, 30, tzinfo=UTC)
    utterances = [
        Utterance(
            meeting_id="m-1",
            speaker_id=f"p-{i}",
            text=f"発言{i}",
            started_at=now,
            ended_at=now,
            duration_sec=1.0,
        )
        for i in range(200)
    ]
    await agent.run(_meeting(), utterances=utterances)

    user_text = agent._chat.call_args.args[0]
    # 200 件全てではなく、上限内の件数 + sentinel
    assert "発言0" in user_text
    assert "発言199" in user_text
    # 中央付近 (index 100) はカットされて出てこない可能性が高い
    assert user_text.count("\"text\": \"発言") <= 110


@pytest.mark.asyncio
async def test_topic_evidence_and_state_included_in_context(monkeypatch):
    """topics の evidence_quote と state が JSON context に乗る。"""
    agent = MeetingReportGenerator()
    monkeypatch.setattr(agent, "_chat", AsyncMock(return_value="ok"))

    await agent.run(_meeting())

    user_text = agent._chat.call_args.args[0]
    assert "Go/NoGo 判定" in user_text
    assert "9 月 15 日で Go で行きましょう" in user_text
    assert "decided" in user_text
    assert "discussing" in user_text
