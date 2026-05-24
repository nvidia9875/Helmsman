"""Tone (発言感情) の in-memory cache + 集約 (Phase 8)。

ToneAgent が 1 度分類した結果を utterance_id でキャッシュ。
同じ utterance を毎 tick 再分類するのは無駄なので。

スレッドセーフ: asyncio.Lock。プロセス再起動で消えるが Cosmos 永続化はしない
(感情ラベルはあくまでリアルタイム UI 用、レポート生成には別途まとめる)。
"""
from __future__ import annotations

import asyncio
from collections import Counter, OrderedDict, deque

from helmsman.models.tone import (
    EmotionLabel,
    MeetingMood,
    MeetingToneSummary,
    ParticipantMood,
    UtteranceTone,
)

# 1 会議あたり保持する分類済 utterance の上限 (古い順に捨てる)
DEFAULT_MAX_PER_MEETING = 200
# ParticipantMood.recent_emotions の長さ
RECENT_EMOTIONS_WINDOW = 8


class ToneBuffer:
    """meeting_id → utterance_id → UtteranceTone の LRU 風キャッシュ。"""

    def __init__(self, max_per_meeting: int = DEFAULT_MAX_PER_MEETING) -> None:
        # OrderedDict は insertion order を保持、頭から捨てれば FIFO/LRU 相当
        self._cache: dict[str, OrderedDict[str, UtteranceTone]] = {}
        self._lock = asyncio.Lock()
        self._max = max_per_meeting

    async def get_unclassified_ids(
        self, meeting_id: str, utterance_ids: list[str]
    ) -> list[str]:
        """まだ分類されてない utterance_id を返す (ToneAgent が次に処理する対象)。"""
        async with self._lock:
            cached = self._cache.get(meeting_id)
            if cached is None:
                return list(utterance_ids)
            return [uid for uid in utterance_ids if uid not in cached]

    async def add(self, meeting_id: str, tones: list[UtteranceTone]) -> None:
        """分類結果を cache に追加。max を超えた古い分は捨てる。"""
        if not tones:
            return
        async with self._lock:
            bucket = self._cache.setdefault(meeting_id, OrderedDict())
            for t in tones:
                # 既存 key を更新する場合は順序を最後尾に
                if t.utterance_id in bucket:
                    bucket.pop(t.utterance_id)
                bucket[t.utterance_id] = t
            while len(bucket) > self._max:
                bucket.popitem(last=False)

    async def get_all(self, meeting_id: str) -> list[UtteranceTone]:
        """meeting の全 cache を発言時刻順 (= insertion order) で返す。"""
        async with self._lock:
            bucket = self._cache.get(meeting_id)
            if not bucket:
                return []
            return list(bucket.values())

    async def clear(self, meeting_id: str) -> None:
        async with self._lock:
            self._cache.pop(meeting_id, None)


_buffer: ToneBuffer | None = None


def get_tone_buffer() -> ToneBuffer:
    global _buffer
    if _buffer is None:
        _buffer = ToneBuffer()
    return _buffer


# ===== 集約: UtteranceTone リスト → MeetingToneSummary =====


def _dominant_emotion(emotions: list[EmotionLabel]) -> EmotionLabel:
    """頻度最多。同数なら配列で先に出た方 (= 新しい方) を返す。"""
    if not emotions:
        return EmotionLabel.NEUTRAL
    counter: Counter[EmotionLabel] = Counter(emotions)
    return counter.most_common(1)[0][0]


def _classify_overall_mood(
    emotions: list[EmotionLabel], sentiment_avg: float
) -> MeetingMood:
    """感情分布と sentiment 平均から会議の温度感を決める。

    ルール (rule-first、後で調整可能):
      - concern + frustration が 40% 以上 → TENSE
      - agreement 30% 以上 + sentiment > 0.2 → ALIGNED
      - joy + curiosity が 40% 以上 → ENERGETIC
      - 上記いずれも当てはまらない → STUCK
    """
    if not emotions:
        return MeetingMood.STUCK
    n = len(emotions)
    counts: Counter[EmotionLabel] = Counter(emotions)
    tense_ratio = (counts[EmotionLabel.CONCERN] + counts[EmotionLabel.FRUSTRATION]) / n
    energetic_ratio = (counts[EmotionLabel.JOY] + counts[EmotionLabel.CURIOSITY]) / n
    agreement_ratio = counts[EmotionLabel.AGREEMENT] / n

    if tense_ratio >= 0.4:
        return MeetingMood.TENSE
    if agreement_ratio >= 0.3 and sentiment_avg > 0.2:
        return MeetingMood.ALIGNED
    if energetic_ratio >= 0.4:
        return MeetingMood.ENERGETIC
    return MeetingMood.STUCK


def summarize(
    meeting_id: str, tones: list[UtteranceTone]
) -> MeetingToneSummary:
    """ToneBuffer の中身 → 集約 summary を作る。

    話者別: 直近 RECENT_EMOTIONS_WINDOW 件で dominant + sentiment 平均を計算。
    全体: 全 tones から overall mood を分類。
    """
    if not tones:
        return MeetingToneSummary(meeting_id=meeting_id, utterance_count=0)

    # 話者別グルーピング (発言順は保持)
    per_speaker: dict[str, deque[UtteranceTone]] = {}
    for t in tones:
        per_speaker.setdefault(t.speaker_id, deque(maxlen=RECENT_EMOTIONS_WINDOW)).append(t)

    moods: list[ParticipantMood] = []
    for sid, items in per_speaker.items():
        items_list = list(items)
        emotions = [it.emotion for it in items_list]
        sentiments = [it.sentiment for it in items_list]
        # display name は最新の cache 項目のものを採用 (途中で改名された場合の最新優先)
        speaker_name = next(
            (it.speaker_name for it in reversed(items_list) if it.speaker_name),
            None,
        )
        moods.append(
            ParticipantMood(
                speaker_id=sid,
                speaker_name=speaker_name,
                sample_count=len(items_list),
                dominant_emotion=_dominant_emotion(emotions),
                sentiment_avg=sum(sentiments) / len(sentiments),
                # UI 表示用に「最新 → 古い」順
                recent_emotions=list(reversed(emotions)),
            )
        )

    # 全体: 単純に全 tones を平均/集約
    overall_sentiment = sum(t.sentiment for t in tones) / len(tones)
    overall_mood = _classify_overall_mood(
        [t.emotion for t in tones], overall_sentiment
    )

    return MeetingToneSummary(
        meeting_id=meeting_id,
        utterance_count=len(tones),
        participant_moods=sorted(moods, key=lambda m: -m.sample_count),
        per_utterance=tones,
        overall_mood=overall_mood,
        overall_sentiment=overall_sentiment,
    )
