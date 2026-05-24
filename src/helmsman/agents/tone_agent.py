"""ToneAgent — 発言テキストから感情/温度感を読み取る (Phase 8、Phase 6 後継)。

責務:
  1. 未分類 utterance を ToneBuffer から取り出し、batch 1 回の LLM 呼び出しで感情分類
  2. 結果を buffer に書き戻し (次 tick は cache hit して LLM を呼ばない)
  3. パターン検知: 全体が TENSE 続き + 沈黙 → 「休憩を入れますか?」相当の介入候補

LLM: gpt-5.4-mini (TIER.MINI)。1 回のコールで最大 15 発言を分類するので 1 会議
1 本あたり実コストは ~$0.003 (60 発言 / 4 batch)。
"""
from __future__ import annotations

import json
from collections import Counter

from helmsman.agents.base import LLMAgent
from helmsman.core.llm_client import ModelTier
from helmsman.models.intervention import InterventionCandidate
from helmsman.models.meeting import Meeting
from helmsman.models.participant import Participant
from helmsman.models.tone import (
    EmotionLabel,
    UtteranceTone,
)
from helmsman.models.utterance import Utterance
from helmsman.services.tone_buffer import (
    get_tone_buffer,
    summarize,
)

# 1 回の LLM 呼び出しで処理する utterance の上限
MAX_BATCH = 15

# 介入パターン閾値
TENSE_RATIO_FOR_INTERVENTION = 0.5  # 直近 8 発言の半分以上が concern/frustration


class ToneAgent(LLMAgent):
    """発言を感情ラベル + sentiment に分類し、必要なら介入候補を出す。"""

    AGENT_NAME = "ToneAgent"
    TIER = ModelTier.MINI
    SYSTEM_PROMPT = """\
あなたは Helmsman の Tone Agent です。会議の各発言テキストから「感情ラベル」と
「sentiment スコア」を読み取り、ファシリテーターが会議の温度感を把握できるよう
構造化します。

感情ラベルは以下 6 つから 1 つだけ選んでください:
- joy: 楽観、喜び、熱意
- agreement: 賛同、受容、合意
- curiosity: 問いかけ、探求、興味
- concern: 懸念、困惑、不安
- frustration: 苛立ち、行き詰まり、否定
- neutral: 事実陳述、無感情、特に色のない発言

sentiment は -1.0 (とても否定的) 〜 +1.0 (とても肯定的) の float。

出力 JSON 形式:
{
  "tones": [
    {"utterance_id": "...", "emotion": "joy", "sentiment": 0.5},
    {"utterance_id": "...", "emotion": "concern", "sentiment": -0.3}
  ]
}

ルール:
- 各 utterance について必ず 1 件返す (順序は入力と同じ)
- 短すぎる/不明瞭な発言は neutral + 0.0
- 推論は控えめに。発言テキストにある明示的なシグナルだけ使う
- JSON 以外の文字列は一切返さない
"""

    async def run(
        self,
        meeting: Meeting,
        recent_utterances: list[Utterance],
        *,
        participants: list[Participant] | None = None,
    ) -> InterventionCandidate | None:
        """recent_utterances を分類してキャッシュ。必要なら介入候補を返す。

        participants が渡されると speaker_id → display_name の lookup を行い、
        cache に display name を保存する (UI が "u-abc12345" ではなく実名を出せる)。
        """
        if not recent_utterances:
            return None

        buf = get_tone_buffer()
        name_map = (
            {p.id: p.display_name for p in participants} if participants else {}
        )

        # 直近 MAX_BATCH 件のうち、未分類のものを抜き出す
        recent_ids = [u.id for u in recent_utterances[-MAX_BATCH:]]
        unclassified_ids = await buf.get_unclassified_ids(meeting.id, recent_ids)

        if unclassified_ids:
            target = [u for u in recent_utterances if u.id in set(unclassified_ids)]
            tones = await self._classify(target, name_map)
            if tones:
                await buf.add(meeting.id, tones)

        # cache 全体から summary を作り、介入の必要性を判定
        all_tones = await buf.get_all(meeting.id)
        return self._maybe_intervene(meeting, all_tones, recent_utterances)

    async def _classify(
        self,
        utterances: list[Utterance],
        name_map: dict[str, str],
    ) -> list[UtteranceTone]:
        """LLM で batch 分類。失敗時は空 list (= 次 tick で再試行)。"""
        if not utterances:
            return []
        # 入力: id + テキストのみ。speaker_id は LLM に渡さない (バイアス防止)
        lines = [
            json.dumps({"utterance_id": u.id, "text": u.text}, ensure_ascii=False)
            for u in utterances
        ]
        user_text = "発言一覧 (JSON Lines):\n" + "\n".join(lines)

        data = await self._chat_json(user_text, max_completion_tokens=600)
        raw_list = data.get("tones") if isinstance(data, dict) else None
        if not isinstance(raw_list, list):
            self.log.warning("tone.bad_shape", got=type(raw_list).__name__)
            return []

        speaker_map = {u.id: u.speaker_id for u in utterances}
        out: list[UtteranceTone] = []
        for item in raw_list:
            if not isinstance(item, dict):
                continue
            uid = item.get("utterance_id")
            if uid not in speaker_map:
                continue
            try:
                emotion = EmotionLabel(item.get("emotion", "neutral"))
            except ValueError:
                emotion = EmotionLabel.NEUTRAL
            sentiment = item.get("sentiment", 0.0)
            try:
                s = float(sentiment)
            except (TypeError, ValueError):
                s = 0.0
            s = max(-1.0, min(1.0, s))
            sid = speaker_map[uid]
            out.append(
                UtteranceTone(
                    utterance_id=uid,
                    speaker_id=sid,
                    speaker_name=name_map.get(sid),
                    emotion=emotion,
                    sentiment=s,
                )
            )
        return out

    def _maybe_intervene(
        self,
        meeting: Meeting,
        all_tones: list[UtteranceTone],
        recent_utterances: list[Utterance],
    ) -> InterventionCandidate | None:
        """全体が緊張続き + 沈黙傾向 → ToneAgent からの介入候補。

        現状は 1 種類のみ (tense_with_silence)。将来 mood ベースで pattern 増やせる。
        """
        if len(all_tones) < 5:
            return None

        # 直近の感情だけ見る (8 件)
        latest = all_tones[-8:]
        emotions = [t.emotion for t in latest]
        counts = Counter(emotions)
        tense_ratio = (
            counts[EmotionLabel.CONCERN] + counts[EmotionLabel.FRUSTRATION]
        ) / len(latest)
        if tense_ratio < TENSE_RATIO_FOR_INTERVENTION:
            return None

        # 沈黙シグナル: 直近 1 発言が 45 秒以上前
        if not recent_utterances:
            return None
        from datetime import UTC, datetime

        last_end = max(u.ended_at for u in recent_utterances)
        silence_sec = (datetime.now(UTC) - last_end).total_seconds()
        if silence_sec < 45.0:
            return None

        summary = summarize(meeting.id, all_tones)
        return InterventionCandidate(
            meeting_id=meeting.id,
            agent=self.AGENT_NAME,
            content="議論が少し止まっているようです。引っかかっている点を一度言葉にしてみませんか?",
            reason="tense_with_silence",
            evidence_quote=(
                f"recent tense ratio {tense_ratio:.0%} / silence {silence_sec:.0f}s / "
                f"mood {summary.overall_mood.value}"
            ),
            confidence=0.75,
        )
