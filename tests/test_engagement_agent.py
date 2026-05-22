"""EngagementAgent — Phase 6 の 10 番目 agent の単体テスト。

LLM は呼ばないので、buffer に投入したシグナルから期待 candidate が出るか
を rule single-pass で検証する。
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from helmsman.agents.engagement_agent import EngagementAgent
from helmsman.models.face_signal import FaceSignalBatch, FaceWindow
from helmsman.models.meeting import Meeting, MeetingMode, MeetingState
from helmsman.models.topic import Topic, TopicPriority, TopicState
from helmsman.models.utterance import Utterance
from helmsman.services.face_signal_buffer import (
    FaceSignalBuffer,
    get_face_signal_buffer,
)


@pytest.fixture(autouse=True)
def clean_buffer():
    """各テスト前後で global buffer をクリアし isolation を保つ。"""
    buf = get_face_signal_buffer()
    # singleton を差し替えるよりクリアしたほうがシンプル
    buf._buffers.clear()
    yield
    buf._buffers.clear()


def _meeting(
    *,
    topics: list[Topic] | None = None,
) -> Meeting:
    return Meeting(
        id="m1",
        organizer_id="u1",
        goal="ローンチ",
        mode=MeetingMode.DECISION,
        state=MeetingState.IN_PROGRESS,
        started_at=datetime.now(UTC),
        topics=topics or [],
    )


def _topic(
    name: str = "価格",
    state: TopicState = TopicState.DISCUSSING,
    last_mention_min_ago: float = 0,
) -> Topic:
    return Topic(
        name=name,
        decision_criteria="¥価格決定",
        time_budget_pct=30,
        priority=TopicPriority.CRITICAL,
        state=state,
        last_mention_at=datetime.now(UTC) - timedelta(minutes=last_mention_min_ago),
    )


def _utterance(text: str, ago_sec: float = 0) -> Utterance:
    end = datetime.now(UTC) - timedelta(seconds=ago_sec)
    return Utterance(
        meeting_id="m1",
        speaker_id="s1",
        text=text,
        started_at=end - timedelta(seconds=2),
        ended_at=end,
        duration_sec=2.0,
    )


def _push_window(
    *,
    confusion: float = 0.0,
    engagement: float = 0.9,
    nods: int = 0,
    participant: str = "p1",
    received_at_ms: float = 1_000.0,
) -> None:
    """buffer に 1 window 投入するヘルパ。"""
    buf = get_face_signal_buffer()
    batch = FaceSignalBatch(
        meeting_id="m1",
        organizer_id="u1",
        participant_id=participant,
        windows=[
            FaceWindow(
                window_start_ms=0.0,
                sample_count=20,
                nod_count=nods,
                confusion=confusion,
                engagement=engagement,
                face_visible_ratio=1.0,
            )
        ],
    )
    import asyncio

    asyncio.get_event_loop().run_until_complete(
        buf.append_batch(batch, server_received_at_ms=received_at_ms)
    )


# ===== 何もシグナルがないなら何も言わない =====


@pytest.mark.asyncio
async def test_returns_none_when_no_face_signals():
    agent = EngagementAgent()
    m = _meeting(topics=[_topic()])
    result = await agent.run(m, recent_utterances=[])
    assert result is None


# ===== パターン A: confusion + silence =====


@pytest.mark.asyncio
async def test_pattern_a_fires_on_high_confusion_and_silence():
    buf = get_face_signal_buffer()
    batch = FaceSignalBatch(
        meeting_id="m1",
        organizer_id="u1",
        participant_id="p1",
        windows=[
            FaceWindow(
                window_start_ms=float(i * 2000),
                sample_count=20,
                nod_count=0,
                confusion=0.8,  # high
                engagement=0.5,
                face_visible_ratio=1.0,
            )
            for i in range(3)
        ],
    )
    await buf.append_batch(batch, server_received_at_ms=10_000.0)

    agent = EngagementAgent()
    m = _meeting(topics=[_topic()])
    # 直近発言は 2 分前 → 60 秒沈黙 OK
    result = await agent.run(m, recent_utterances=[_utterance("古い発言", ago_sec=120)])
    assert result is not None
    assert result.reason == "visible_confusion_with_silence"
    assert result.confidence >= 0.7


@pytest.mark.asyncio
async def test_pattern_a_does_not_fire_when_just_spoke():
    """直近 5 秒に発言があるなら silence 条件を満たさない → 発火しない。"""
    buf = get_face_signal_buffer()
    batch = FaceSignalBatch(
        meeting_id="m1",
        organizer_id="u1",
        participant_id="p1",
        windows=[
            FaceWindow(
                window_start_ms=0,
                sample_count=20,
                nod_count=0,
                confusion=0.9,
                engagement=0.5,
                face_visible_ratio=1.0,
            )
        ]
        * 5,
    )
    await buf.append_batch(batch, server_received_at_ms=10_000.0)

    agent = EngagementAgent()
    m = _meeting(topics=[_topic()])
    result = await agent.run(
        m, recent_utterances=[_utterance("いま喋ったばかり", ago_sec=2)]
    )
    # confusion 高いが silence 条件外 → None
    assert result is None


# ===== パターン B: nod burst =====


@pytest.mark.asyncio
async def test_pattern_b_fires_on_nod_burst_without_confusion():
    buf = get_face_signal_buffer()
    batch = FaceSignalBatch(
        meeting_id="m1",
        organizer_id="u1",
        participant_id="p1",
        windows=[
            FaceWindow(
                window_start_ms=0,
                sample_count=20,
                nod_count=8,
                confusion=0.1,
                engagement=0.9,
                face_visible_ratio=1.0,
            )
        ],
    )
    await buf.append_batch(batch, server_received_at_ms=10_000.0)

    agent = EngagementAgent()
    m = _meeting(topics=[_topic()])
    # 直近に発言あるが、A は confusion 不足、C は engagement OK で発火しない → B が残る
    result = await agent.run(
        m, recent_utterances=[_utterance("はい", ago_sec=1)]
    )
    assert result is not None
    assert result.reason == "nod_burst_consensus"


@pytest.mark.asyncio
async def test_pattern_b_skipped_when_confusion_high():
    buf = get_face_signal_buffer()
    batch = FaceSignalBatch(
        meeting_id="m1",
        organizer_id="u1",
        participant_id="p1",
        windows=[
            FaceWindow(
                window_start_ms=0,
                sample_count=20,
                nod_count=10,
                confusion=0.5,  # nod 多いが困惑も中程度 → "合意とは限らない"
                engagement=0.9,
                face_visible_ratio=1.0,
            )
        ],
    )
    await buf.append_batch(batch, server_received_at_ms=10_000.0)

    agent = EngagementAgent()
    m = _meeting(topics=[_topic()])
    # confusion 中で direct 発言あるので silence なし → A 不発、B は閾値で skip
    result = await agent.run(
        m, recent_utterances=[_utterance("はい", ago_sec=1)]
    )
    # 高 confusion でも silence 条件外 → A 不発、B は high confusion で skip
    assert result is None or result.reason != "nod_burst_consensus"


# ===== パターン C: low engagement + 同 topic 5 分以上 =====


@pytest.mark.asyncio
async def test_pattern_c_fires_on_low_engagement_and_stuck_topic():
    buf = get_face_signal_buffer()
    batch = FaceSignalBatch(
        meeting_id="m1",
        organizer_id="u1",
        participant_id="p1",
        windows=[
            FaceWindow(
                window_start_ms=float(i * 2000),
                sample_count=20,
                nod_count=0,
                confusion=0.2,  # 低い → A 不発
                engagement=0.2,  # 低い
                face_visible_ratio=1.0,
            )
            for i in range(3)
        ],
    )
    await buf.append_batch(batch, server_received_at_ms=10_000.0)

    agent = EngagementAgent()
    long_topic = _topic(state=TopicState.DEEP_DIVE, last_mention_min_ago=6.0)
    m = _meeting(topics=[long_topic])
    # 直近発言があり silence 条件 NG (A 不発)
    result = await agent.run(
        m, recent_utterances=[_utterance("えー…", ago_sec=2)]
    )
    assert result is not None
    assert result.reason == "low_engagement_stuck_topic"
    assert "価格" in result.content


@pytest.mark.asyncio
async def test_pattern_c_skipped_when_topic_is_fresh():
    """同 topic が 5 分未満なら C は不発。"""
    buf = get_face_signal_buffer()
    batch = FaceSignalBatch(
        meeting_id="m1",
        organizer_id="u1",
        participant_id="p1",
        windows=[
            FaceWindow(
                window_start_ms=0,
                sample_count=20,
                nod_count=0,
                confusion=0.2,
                engagement=0.2,
                face_visible_ratio=1.0,
            )
        ]
        * 4,
    )
    await buf.append_batch(batch, server_received_at_ms=10_000.0)

    agent = EngagementAgent()
    fresh_topic = _topic(last_mention_min_ago=1.0)
    m = _meeting(topics=[fresh_topic])
    result = await agent.run(
        m, recent_utterances=[_utterance("少し進んだ", ago_sec=2)]
    )
    assert result is None


# ===== 優先度: A が C より優先 =====


@pytest.mark.asyncio
async def test_pattern_a_outranks_pattern_c_when_both_match():
    """両方該当する場合は A (個別ケア優先) が返る。"""
    buf = get_face_signal_buffer()
    batch = FaceSignalBatch(
        meeting_id="m1",
        organizer_id="u1",
        participant_id="p1",
        windows=[
            FaceWindow(
                window_start_ms=float(i * 2000),
                sample_count=20,
                nod_count=0,
                confusion=0.8,  # A 該当
                engagement=0.2,  # C も該当
                face_visible_ratio=1.0,
            )
            for i in range(3)
        ],
    )
    await buf.append_batch(batch, server_received_at_ms=10_000.0)

    agent = EngagementAgent()
    long_topic = _topic(state=TopicState.DEEP_DIVE, last_mention_min_ago=6.0)
    m = _meeting(topics=[long_topic])
    result = await agent.run(
        m, recent_utterances=[_utterance("古い", ago_sec=120)]
    )
    assert result is not None
    assert result.reason == "visible_confusion_with_silence"
