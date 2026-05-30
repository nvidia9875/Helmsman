"""Intervention Arbiter — 全エージェントの介入候補を調停する。

これが Helmsman の新規性の核:
- Density-aware silence (活発な時こそ AI が黙る)
- Mode-conditional priority (会議モードで重み変動)
- Authority gradient (上司発言中は弱介入抑制)
- Two-side simultaneous L3 injection (将来: 物理 + リモート)
"""
from __future__ import annotations

from datetime import UTC, datetime

from helmsman.core.llm_client import ModelTier
from helmsman.core.logging import logger
from helmsman.models.intervention import (
    InterventionCandidate,
    InterventionDelivery,
    InterventionLevel,
)
from helmsman.models.meeting import Meeting, UserIntensity
from helmsman.models.participant import Participant


class InterventionArbiter:
    """6 + 1 エージェントの介入候補を集約 → 1 つ選択 → 配信決定。"""

    AGENT_NAME = "Arbiter"
    TIER = ModelTier.MINI  # ルールベース中心、軽量

    # エージェント優先度
    PRIORITY: dict[str, int] = {
        "DecisionCapture": 100,
        "TimeKeeper": 80,
        "SteeringAgent": 70,
        "MemoryRetriever": 65,  # Phase 7: Steering と Dissent の間
        "DissentSurface": 60,
        "ToneAgent": 55,  # 感情シグナル: Dissent と Quiet の間
        "QuietActivator": 50,
        "DevilsAdvocate": 40,  # 将来分
        "GoalDecomposer": 30,  # 通常は decide 直後のみ
    }

    RATE_LIMIT_SEC = 60          # 通常は 1 介入 / 分
    HIGH_PRIORITY_RATE_LIMIT = 20  # priority>=80 は 20 秒に短縮

    USER_INTENSITY_THRESHOLDS = {
        UserIntensity.QUIET: 80,       # priority>=80 のみ通す
        UserIntensity.NORMAL: 50,
        UserIntensity.AGGRESSIVE: 0,
    }

    def __init__(self) -> None:
        self.log = logger.bind(agent=self.AGENT_NAME)

    def decide(
        self,
        candidates: list[InterventionCandidate],
        meeting: Meeting,
        chair: Participant | None,
        current_speaker: Participant | None,
        now: datetime | None = None,
    ) -> InterventionDelivery | None:
        """候補リストから 0 or 1 件の delivery を返す。

        `now` を指定すると rate_limit の比較基準時刻を上書きできる (eval で audio
        time を使うため)。None なら datetime.now(UTC)。
        """
        # 1) confidence フィルタ
        candidates = [c for c in candidates if c.confidence >= 0.7]
        if not candidates:
            return None

        # 2) 優先度ソート
        # ToneAgent の "tense_with_silence" は通常 55 だが、個別ケアの即時性が
        # 高いので +20 boost (Steering 70 と並ぶ)。consensus / stuck はそのまま 55。
        def _effective_priority(c: InterventionCandidate) -> int:
            base = self.PRIORITY.get(c.agent, 0)
            if c.agent == "ToneAgent" and c.reason == "tense_with_silence":
                return base + 20
            return base

        candidates.sort(key=_effective_priority, reverse=True)

        ref_now = now or datetime.now(UTC)
        for c in candidates:
            if not self._can_intervene(c, meeting, current_speaker, ref_now):
                self.log.debug("arbiter.skipped", agent=c.agent, reason="filter")
                continue
            level = self._intervention_level(c, meeting)
            audience = self._audience(c, level, chair)
            self.log.info(
                "arbiter.deliver",
                agent=c.agent,
                level=level.value,
                priority=self.PRIORITY.get(c.agent, 0),
            )
            return InterventionDelivery(
                meeting_id=meeting.id,
                candidate_id=c.id,
                agent=c.agent,
                content=c.content,
                reason=c.reason,
                evidence_quote=c.evidence_quote,
                level=level,
                audience=audience,
            )

        return None

    def _can_intervene(
        self,
        c: InterventionCandidate,
        meeting: Meeting,
        current_speaker: Participant | None,
        now: datetime,
    ) -> bool:
        priority = self.PRIORITY.get(c.agent, 0)

        # rate limit (intensity による調整)
        # AGGRESSIVE モードではレートを半減し、短時間会議 (3-5 分のデモ等) でも
        # 複数 agent (Dissent / Steering / ToneAgent) が連続発火できるようにする。
        base_rate = self.RATE_LIMIT_SEC
        high_rate = self.HIGH_PRIORITY_RATE_LIMIT
        if meeting.user_intensity == UserIntensity.AGGRESSIVE:
            base_rate = base_rate // 2  # 60s → 30s
            high_rate = high_rate // 2  # 20s → 10s
        rate_limit = high_rate if priority >= 80 else base_rate
        if meeting.last_intervention_at is not None:
            elapsed = (now - meeting.last_intervention_at).total_seconds()
            if elapsed < rate_limit:
                return False

        # density-aware silence (AGGRESSIVE はより寛容に、議論密度が高くても通す)
        density_threshold = (
            0.95 if meeting.user_intensity == UserIntensity.AGGRESSIVE else 0.8
        )
        if meeting.recent_utterance_density > density_threshold and priority < 80:
            return False

        # authority gradient: 上司発言中は弱介入抑制
        if current_speaker and current_speaker.is_senior and priority < 70:
            return False

        # user intensity setting
        threshold = self.USER_INTENSITY_THRESHOLDS[meeting.user_intensity]
        if priority < threshold:
            return False

        # mode whitelist (空ならすべて許可)
        if c.allowed_modes and meeting.mode.value not in c.allowed_modes:
            return False

        # 内容重複の抑制: 直近に配信した介入とほぼ同一内容なら出さない。
        # AGGRESSIVE で頻度が上がると DecisionCapture が同じ決定を毎 tick 再 announce
        # したり Steering が同じ nudge を繰り返すため、near-dup を弾く。
        if self._is_dup_content(c.content, meeting):
            return False

        return True

    @staticmethod
    def _norm_for_dup(s: str) -> str:
        import re as _re
        # 空白・句読点を除去して比較用に正規化 (句読点違いの near-dup も拾う)
        return _re.sub(r"[\s、。，．,.!?！？・:：]+", "", s)

    def _is_dup_content(self, content: str, meeting: Meeting) -> bool:
        """直近に配信した介入とほぼ同一内容かを判定 (difflib 類似度 >= 0.85)。"""
        import difflib

        target = self._norm_for_dup(content)
        if not target:
            return False
        for d in meeting.delivered_interventions[-8:]:
            prev = self._norm_for_dup(getattr(d, "content", "") or "")
            if not prev:
                continue
            if difflib.SequenceMatcher(None, target, prev).ratio() >= 0.85:
                return True
        return False

    def _intervention_level(
        self, c: InterventionCandidate, meeting: Meeting
    ) -> InterventionLevel:
        priority = self.PRIORITY.get(c.agent, 0)
        time_left = meeting.time_remaining_pct

        # L3 (音声介入) の昇格条件:
        # - 通常 (NORMAL/QUIET): time_left < 0.20 かつ priority >= 80
        #   (60 分会議の終盤、重要な決定だけが声で介入)
        # - AGGRESSIVE: 時間条件を外し、priority >= 80 なら常に L3
        #   (デモや短時間会議で音声介入をデモするためのモード)
        #   rate_limit (AGGRESSIVE で 10 秒) が頻度を制御し、結果として
        #   おおむね 30 秒-1 分に 1 回のペースで bot が音声発話する
        l3_unlocked = (
            meeting.user_intensity == UserIntensity.AGGRESSIVE
            or time_left < 0.20
        )
        if l3_unlocked and priority >= 80:
            return InterventionLevel.L3

        # L2: 中・高優先度
        if priority >= 50:
            return InterventionLevel.L2

        # L1: 低優先度 (司会のみ)
        return InterventionLevel.L1

    def _audience(
        self,
        c: InterventionCandidate,
        level: InterventionLevel,
        chair: Participant | None,
    ) -> list[str]:
        if level == InterventionLevel.L1:
            return [chair.id] if chair else ["chair"]
        if level == InterventionLevel.L2:
            return ["all"]
        # L3: 物理 + リモート両側に同時音声注入 (将来実装)
        return ["room_speaker", "remote_audio_inject"]
