"""Tone / 感情モデル (Phase 8 = 顔シグナル後継)。

会議の発言テキストから「感情ラベル + sentiment + 全体の温度感」を取り出す。
Phase 6 の MediaPipe / カメラ路線は撤去し、テキスト/音声文脈ベースに置き換え。
"""
from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, Field


class EmotionLabel(str, Enum):
    """1 発言の感情ラベル。LLM が「直近の発言テキスト」だけから推定する。

    意図的に少数 (6 つ) に絞る:
      - LLM のラベル安定性
      - UI バッジの絵文字 1 対 1 対応
      - 全体 mood の集計が単純になる
    """

    JOY = "joy"               # 😊  楽観・喜び
    AGREEMENT = "agreement"   # 👍  賛同・受容
    CURIOSITY = "curiosity"   # 🤔  問い・探求
    CONCERN = "concern"       # 😕  懸念・困惑
    FRUSTRATION = "frustration"  # 😤  苛立ち・行き詰まり
    NEUTRAL = "neutral"       # 😐  事実陳述・無感情


# LLM へ提示するラベル一覧。並び順は変えないこと (Prompt の安定性のため)。
EMOTION_LABELS: tuple[EmotionLabel, ...] = (
    EmotionLabel.JOY,
    EmotionLabel.AGREEMENT,
    EmotionLabel.CURIOSITY,
    EmotionLabel.CONCERN,
    EmotionLabel.FRUSTRATION,
    EmotionLabel.NEUTRAL,
)

# UI 用の絵文字マップ (英訳出ない場合の表記揺れを防ぐためサーバー側で持つ)
EMOTION_EMOJI: dict[EmotionLabel, str] = {
    EmotionLabel.JOY: "😊",
    EmotionLabel.AGREEMENT: "👍",
    EmotionLabel.CURIOSITY: "🤔",
    EmotionLabel.CONCERN: "😕",
    EmotionLabel.FRUSTRATION: "😤",
    EmotionLabel.NEUTRAL: "😐",
}


class MeetingMood(str, Enum):
    """会議全体の「温度感」。speaker mood の集約から決定する。"""

    ALIGNED = "aligned"       # 合意ベース・前向き (agreement 多い、sentiment 高)
    ENERGETIC = "energetic"   # 活発・探求 (joy + curiosity 多い)
    TENSE = "tense"           # 緊張・困惑 (concern + frustration 多い)
    STUCK = "stuck"           # 停滞・無感情 (neutral が支配的 + sentiment 中立)


class UtteranceTone(BaseModel):
    """1 発言を 1 ラベル + sentiment で表したもの。"""

    utterance_id: str
    speaker_id: str
    # 発言者表示名。tick リクエストに participants が含まれない場合は None。
    speaker_name: str | None = None
    emotion: EmotionLabel
    sentiment: float = Field(ge=-1.0, le=1.0)
    classified_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ParticipantMood(BaseModel):
    """話者ごとの集約 mood。直近 N 発言の傾向。"""

    speaker_id: str
    # cache 内で最後に確認された display name。未取得なら None (UI は id 短縮表示)
    speaker_name: str | None = None
    sample_count: int
    dominant_emotion: EmotionLabel
    sentiment_avg: float = Field(ge=-1.0, le=1.0)
    # 最新 → 古い順、UI で badge stream として表示する
    recent_emotions: list[EmotionLabel] = Field(default_factory=list)


class MeetingToneSummary(BaseModel):
    """会議全体の最新 mood サマリ — API レスポンス本体。

    UI はこれだけで:
      - 発言ごとの感情バッジ (per_utterance)
      - 話者別 mood (participant_moods)
      - 全体 mood meter (overall_mood, overall_sentiment)
    を描ける。
    """

    meeting_id: str
    utterance_count: int  # cache 済の発言数
    participant_moods: list[ParticipantMood] = Field(default_factory=list)
    per_utterance: list[UtteranceTone] = Field(default_factory=list)
    overall_mood: MeetingMood = MeetingMood.STUCK
    overall_sentiment: float = 0.0
    last_updated: datetime = Field(default_factory=lambda: datetime.now(UTC))
