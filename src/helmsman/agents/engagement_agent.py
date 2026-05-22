"""Engagement Agent (Phase 6) — 顔シグナルを文脈に合わせた介入候補に変換。

10 番目の agent。FaceSignalBuffer の直近 5 分の集計サマリ + 直近発言を
読み、以下のパターンを rule-first で検出する (ADR-108):

  A) 高 confusion + 沈黙が続く
     → 「もう少し聞きたい点はありますか?」L2 candidate
  B) 全員 nodding + 同意発言
     → 「決まりそうですね」decision を後押し
  C) engagement 全体低下 + 同じ topic > 5 min
     → 「方向性を一度確認しましょうか」(Steering 後押し)

LLM は呼ばない (rule のみ)。コスト保護 + レイテンシ。
将来的に LLM 経由の細やかな表現生成にしたければ、 _llm_polish を差し込める。
"""
from __future__ import annotations

from datetime import UTC, datetime

from helmsman.core.llm_client import ModelTier
from helmsman.core.logging import logger
from helmsman.core.usage import UsageRecord
from helmsman.models.intervention import InterventionCandidate
from helmsman.models.meeting import Meeting
from helmsman.models.topic import Topic, TopicState
from helmsman.models.utterance import Utterance
from helmsman.services.face_signal_buffer import (
    FaceSignalSummary,
    get_face_signal_buffer,
    summarize_windows,
)

# 集計ウィンドウ (face signal の参照範囲)
WINDOW_MS = 180_000  # 3 分

# パターン A: confusion + 沈黙
PATTERN_A_HIGH_CONF_RATIO = 0.4  # high_confusion window が 40% 超
PATTERN_A_SILENCE_SEC = 60.0  # 直近 60 秒以上、新しい発言が無い

# パターン B: nod burst
PATTERN_B_TOTAL_NODS = 6  # 直近 window 合計 nod 6 回以上
PATTERN_B_LOW_CONFUSION = 0.3  # 困惑が落ち着いている

# パターン C: low engagement on same topic
PATTERN_C_LOW_ENG_RATIO = 0.5  # low_engagement 比率 50% 超
PATTERN_C_TOPIC_MINUTES = 5.0  # 同 topic が 5 分以上


class EngagementAgent:
    """Phase 6 の 10 番目 agent。LLM を呼ばず rule-based で candidate を作る。"""

    AGENT_NAME = "EngagementAgent"
    TIER = ModelTier.MINI  # 名目上の tier (実際は LLM 呼ばない)

    def __init__(self) -> None:
        self.log = logger.bind(agent=self.AGENT_NAME)
        # LLM を呼ばないので last_usage は常に None
        self.last_usage: UsageRecord | None = None

    async def run(
        self,
        meeting: Meeting,
        recent_utterances: list[Utterance],
        *,
        now: datetime | None = None,
    ) -> InterventionCandidate | None:
        """直近 face signal + utterance を読み、1 件の candidate を返す (or None)。

        パターンの優先度: A (個別ケアが必要) > C (議論停滞) > B (前向きブースト)。
        最初にヒットしたパターンで return。
        """
        ref_now = now or datetime.now(UTC)

        # 1) face signal 集計 (buffer から、Cosmos は読まない)
        buf = get_face_signal_buffer()
        windows = await buf.recent(meeting.id, within_ms=WINDOW_MS)
        summary = summarize_windows(windows)
        if summary.sample_count == 0:
            return None  # 顔シグナルが流れて来てない → 黙る

        # 2) パターン A: 高 confusion + 沈黙
        cand = self._pattern_a(meeting, summary, recent_utterances, ref_now)
        if cand:
            return cand

        # 3) パターン C: low engagement + 長時間 same topic
        cand = self._pattern_c(meeting, summary, ref_now)
        if cand:
            return cand

        # 4) パターン B: nod burst
        cand = self._pattern_b(meeting, summary)
        if cand:
            return cand

        return None

    # ---------- パターン実装 ----------

    def _pattern_a(
        self,
        meeting: Meeting,
        s: FaceSignalSummary,
        recent_utterances: list[Utterance],
        ref_now: datetime,
    ) -> InterventionCandidate | None:
        """高 confusion + 沈黙 → 個別ケアを促す。"""
        if s.sample_count == 0:
            return None
        high_ratio = s.high_confusion_count / s.sample_count
        if high_ratio < PATTERN_A_HIGH_CONF_RATIO:
            return None
        # 直近発言からの経過秒
        if not recent_utterances:
            silence_sec = float("inf")
        else:
            last_end = max(u.ended_at for u in recent_utterances)
            silence_sec = max(0.0, (ref_now - last_end).total_seconds())
        if silence_sec < PATTERN_A_SILENCE_SEC:
            return None

        return InterventionCandidate(
            meeting_id=meeting.id,
            agent=self.AGENT_NAME,
            content=(
                "もう少し聞きたい点はありますか? "
                "(困惑のサインが続いているようです)"
            ),
            reason="visible_confusion_with_silence",
            evidence_quote=f"confusion {s.mean_confusion:.2f} / silence {silence_sec:.0f}s",
            confidence=0.78,
        )

    def _pattern_b(
        self,
        meeting: Meeting,
        s: FaceSignalSummary,
    ) -> InterventionCandidate | None:
        """全員 nodding + 困惑低い → 決まりそうな空気、Decision を後押し。"""
        if s.total_nods < PATTERN_B_TOTAL_NODS:
            return None
        if s.mean_confusion > PATTERN_B_LOW_CONFUSION:
            return None

        return InterventionCandidate(
            meeting_id=meeting.id,
            agent=self.AGENT_NAME,
            content=(
                "うなずきが多く出ています。決まりそうなら言葉にしておきますか?"
            ),
            reason="nod_burst_consensus",
            evidence_quote=f"nods {s.total_nods} / confusion {s.mean_confusion:.2f}",
            confidence=0.72,
        )

    def _pattern_c(
        self,
        meeting: Meeting,
        s: FaceSignalSummary,
        ref_now: datetime,
    ) -> InterventionCandidate | None:
        """全体的に engagement 低下 + 同じ topic が 5 分以上 → 方向性確認。"""
        if s.sample_count == 0:
            return None
        low_ratio = s.low_engagement_count / s.sample_count
        if low_ratio < PATTERN_C_LOW_ENG_RATIO:
            return None
        active = _pick_long_running_topic(meeting.topics, ref_now)
        if active is None:
            return None

        return InterventionCandidate(
            meeting_id=meeting.id,
            agent=self.AGENT_NAME,
            content=(
                f"「{active.name}」が長くなっています。一度方向性を確認しましょうか?"
            ),
            reason="low_engagement_stuck_topic",
            evidence_quote=f"engagement {s.mean_engagement:.2f}",
            confidence=0.7,
        )


def _pick_long_running_topic(
    topics: list[Topic], ref_now: datetime
) -> Topic | None:
    """deep_dive/discussing で last_mention_at から 5 分以上 経った topic を選ぶ。"""
    for state in (TopicState.DEEP_DIVE, TopicState.DISCUSSING):
        for t in topics:
            if t.state != state or t.last_mention_at is None:
                continue
            elapsed_min = (ref_now - t.last_mention_at).total_seconds() / 60.0
            if elapsed_min >= PATTERN_C_TOPIC_MINUTES:
                return t
    return None
