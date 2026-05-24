"""ToneAgent (Phase 8、Phase 6 EngagementAgent 後継) の単体テスト。

LLM 呼び出しは mock (_chat_json) して、分類結果が ToneBuffer に正しく
反映されること、介入閾値の境界、集約 mood の rule を検証する。
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from helmsman.agents.tone_agent import (
    TENSE_RATIO_FOR_INTERVENTION,
    ToneAgent,
)
from helmsman.models.meeting import Meeting, MeetingMode, MeetingState
from helmsman.models.tone import (
    EmotionLabel,
    MeetingMood,
    UtteranceTone,
)
from helmsman.models.utterance import Utterance
from helmsman.services.tone_buffer import (
    ToneBuffer,
    _classify_overall_mood,
    _dominant_emotion,
    get_tone_buffer,
    summarize,
)


# ===== fixtures =====


def _meeting(meeting_id: str = "m-test") -> Meeting:
    return Meeting(
        id=meeting_id,
        organizer_id="u-1",
        goal="決めること",
        mode=MeetingMode.DECISION,
        state=MeetingState.IN_PROGRESS,
        started_at=datetime.now(UTC),
    )


def _utt(
    text: str,
    speaker: str = "s1",
    minutes_ago: float = 0.5,
    uid: str | None = None,
) -> Utterance:
    end = datetime.now(UTC) - timedelta(minutes=minutes_ago)
    start = end - timedelta(seconds=3)
    extra = {"id": uid} if uid is not None else {}
    return Utterance(
        meeting_id="m-test",
        speaker_id=speaker,
        text=text,
        started_at=start,
        ended_at=end,
        duration_sec=3.0,
        **extra,
    )


@pytest.fixture(autouse=True)
async def _clear_buffer():
    """各テスト前後で global buffer を初期化 (テスト分離)。"""
    buf = get_tone_buffer()
    await buf.clear("m-test")
    yield
    await buf.clear("m-test")


# ===== _dominant_emotion / _classify_overall_mood =====


def test_dominant_emotion_returns_most_common():
    emotions = [
        EmotionLabel.JOY,
        EmotionLabel.AGREEMENT,
        EmotionLabel.JOY,
        EmotionLabel.NEUTRAL,
    ]
    assert _dominant_emotion(emotions) == EmotionLabel.JOY


def test_dominant_emotion_empty_returns_neutral():
    assert _dominant_emotion([]) == EmotionLabel.NEUTRAL


def test_overall_mood_tense_when_concern_frustration_ratio_high():
    emotions = [
        EmotionLabel.CONCERN,
        EmotionLabel.FRUSTRATION,
        EmotionLabel.NEUTRAL,
        EmotionLabel.NEUTRAL,
        EmotionLabel.AGREEMENT,
    ]
    # 2/5 = 40% → tense 閾値ぴったり
    assert _classify_overall_mood(emotions, sentiment_avg=-0.1) == MeetingMood.TENSE


def test_overall_mood_aligned_when_agreement_and_positive():
    emotions = [
        EmotionLabel.AGREEMENT,
        EmotionLabel.AGREEMENT,
        EmotionLabel.JOY,
        EmotionLabel.NEUTRAL,
    ]
    assert _classify_overall_mood(emotions, sentiment_avg=0.4) == MeetingMood.ALIGNED


def test_overall_mood_energetic_when_joy_curiosity_dominant():
    emotions = [
        EmotionLabel.JOY,
        EmotionLabel.CURIOSITY,
        EmotionLabel.CURIOSITY,
        EmotionLabel.NEUTRAL,
        EmotionLabel.NEUTRAL,
    ]
    # 3/5 = 60% → energetic
    assert _classify_overall_mood(emotions, sentiment_avg=0.1) == MeetingMood.ENERGETIC


def test_overall_mood_stuck_when_only_neutral():
    emotions = [EmotionLabel.NEUTRAL] * 5
    assert _classify_overall_mood(emotions, sentiment_avg=0.0) == MeetingMood.STUCK


# ===== ToneBuffer =====


@pytest.mark.asyncio
async def test_buffer_returns_unclassified_ids():
    buf = ToneBuffer()
    # cache 空 → 全 id が未分類
    ids = await buf.get_unclassified_ids("m-x", ["a", "b", "c"])
    assert ids == ["a", "b", "c"]

    await buf.add(
        "m-x",
        [
            UtteranceTone(
                utterance_id="a",
                speaker_id="s1",
                emotion=EmotionLabel.NEUTRAL,
                sentiment=0.0,
            )
        ],
    )
    ids = await buf.get_unclassified_ids("m-x", ["a", "b", "c"])
    assert ids == ["b", "c"]


@pytest.mark.asyncio
async def test_buffer_caps_at_max_per_meeting():
    buf = ToneBuffer(max_per_meeting=3)
    for i in range(5):
        await buf.add(
            "m-x",
            [
                UtteranceTone(
                    utterance_id=f"u{i}",
                    speaker_id="s1",
                    emotion=EmotionLabel.NEUTRAL,
                    sentiment=0.0,
                )
            ],
        )
    items = await buf.get_all("m-x")
    assert [it.utterance_id for it in items] == ["u2", "u3", "u4"]


# ===== summarize =====


def test_summarize_empty_returns_stuck_mood():
    s = summarize("m-test", [])
    assert s.utterance_count == 0
    assert s.overall_mood == MeetingMood.STUCK
    assert s.participant_moods == []


def test_summarize_groups_by_speaker_and_orders_recent_emotions_newest_first():
    tones = [
        UtteranceTone(
            utterance_id="1",
            speaker_id="s1",
            emotion=EmotionLabel.NEUTRAL,
            sentiment=0.0,
        ),
        UtteranceTone(
            utterance_id="2",
            speaker_id="s1",
            emotion=EmotionLabel.JOY,
            sentiment=0.5,
        ),
        UtteranceTone(
            utterance_id="3",
            speaker_id="s2",
            emotion=EmotionLabel.CONCERN,
            sentiment=-0.4,
        ),
    ]
    s = summarize("m-test", tones)
    assert s.utterance_count == 3
    speakers = {p.speaker_id: p for p in s.participant_moods}
    assert set(speakers.keys()) == {"s1", "s2"}
    # s1: 直近 emotion stream は newest → oldest
    assert speakers["s1"].recent_emotions == [EmotionLabel.JOY, EmotionLabel.NEUTRAL]
    assert speakers["s2"].dominant_emotion == EmotionLabel.CONCERN
    # per_utterance はそのまま保持
    assert len(s.per_utterance) == 3


# ===== ToneAgent.run — LLM mock =====


@pytest.mark.asyncio
async def test_run_classifies_new_utterances_and_caches():
    meeting = _meeting()
    utts = [
        _utt("いいですね、賛成です", speaker="s1", uid="u1"),
        _utt("ちょっと心配な点があります", speaker="s2", uid="u2"),
    ]
    agent = ToneAgent()
    agent._chat_json = AsyncMock(
        return_value={
            "tones": [
                {"utterance_id": "u1", "emotion": "agreement", "sentiment": 0.6},
                {"utterance_id": "u2", "emotion": "concern", "sentiment": -0.3},
            ]
        }
    )

    cand = await agent.run(meeting, utts)
    # cache に入ってる
    all_tones = await get_tone_buffer().get_all(meeting.id)
    assert {t.utterance_id for t in all_tones} == {"u1", "u2"}
    # サンプル数不足なので介入は出ない
    assert cand is None


@pytest.mark.asyncio
async def test_run_skips_llm_when_all_utterances_already_cached():
    meeting = _meeting()
    utts = [_utt("ok", speaker="s1", uid="u1")]
    await get_tone_buffer().add(
        meeting.id,
        [
            UtteranceTone(
                utterance_id="u1",
                speaker_id="s1",
                emotion=EmotionLabel.AGREEMENT,
                sentiment=0.4,
            )
        ],
    )
    agent = ToneAgent()
    agent._chat_json = AsyncMock(return_value={"tones": []})

    await agent.run(meeting, utts)
    agent._chat_json.assert_not_called()


@pytest.mark.asyncio
async def test_run_emits_tense_intervention_when_tense_ratio_and_silence():
    meeting = _meeting()
    # 直近 1 発言を 60 秒前にして「沈黙」を作る
    utts = [_utt("..", speaker="s1", uid="u0", minutes_ago=1.5)]
    # buffer に 6 件の concern/frustration を直接突っ込む (= 100% tense)
    await get_tone_buffer().add(
        meeting.id,
        [
            UtteranceTone(
                utterance_id=f"u{i}",
                speaker_id="s1",
                emotion=EmotionLabel.CONCERN
                if i % 2 == 0
                else EmotionLabel.FRUSTRATION,
                sentiment=-0.4,
            )
            for i in range(6)
        ],
    )
    agent = ToneAgent()
    agent._chat_json = AsyncMock(return_value={"tones": []})

    cand = await agent.run(meeting, utts)
    assert cand is not None
    assert cand.agent == "ToneAgent"
    assert cand.reason == "tense_with_silence"
    assert cand.confidence >= 0.7


@pytest.mark.asyncio
async def test_run_no_intervention_when_tense_but_recent_speech():
    meeting = _meeting()
    # 直近 1 発言を 5 秒前 (= 沈黙ではない)
    utts = [_utt("..", speaker="s1", uid="u0", minutes_ago=5 / 60)]
    await get_tone_buffer().add(
        meeting.id,
        [
            UtteranceTone(
                utterance_id=f"u{i}",
                speaker_id="s1",
                emotion=EmotionLabel.CONCERN,
                sentiment=-0.5,
            )
            for i in range(6)
        ],
    )
    agent = ToneAgent()
    agent._chat_json = AsyncMock(return_value={"tones": []})

    cand = await agent.run(meeting, utts)
    assert cand is None


@pytest.mark.asyncio
async def test_run_handles_malformed_llm_response():
    """LLM が壊れた JSON を返しても agent は黙って続行する。"""
    meeting = _meeting()
    utts = [_utt("hi", uid="u1")]
    agent = ToneAgent()
    agent._chat_json = AsyncMock(return_value={"tones": "not a list"})

    cand = await agent.run(meeting, utts)
    assert cand is None
    # buffer は空のまま
    assert await get_tone_buffer().get_all(meeting.id) == []


def test_tense_threshold_constant_sane():
    """0.5 (= 50% 以上が緊張系) は介入閾値として妥当。回帰防止のスモーク。"""
    assert 0.3 <= TENSE_RATIO_FOR_INTERVENTION <= 0.7
