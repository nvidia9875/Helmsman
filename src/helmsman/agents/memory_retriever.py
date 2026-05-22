"""Memory Retriever — 過去会議の関連決定を引いて「あの時こう決めましたよね」を表面化。

Phase 7 (会議横断記憶) の核となる 9 番目の agent。

二段構成 (ADR-103):
  1. 現在の discussing topic + 直近発言を embed → search_decisions で top_k 取得
  2. MINI tier LLM で「今この場で表に出すべきか」を最終判定
     (単なる類似だけだと過去 decision がノイズ化するため)

重複抑制: meeting.surfaced_decision_ids に追加し、同一会議内では同じ過去決定を
2 回出さない。

LLM 呼び出し回数を抑える gate:
  - discussing 状態の topic が無ければ skip (LLM 呼ばない)
  - vector search のヒットが 0 件なら skip
"""
from __future__ import annotations

from helmsman.agents.base import LLMAgent
from helmsman.core.llm_client import ModelTier
from helmsman.core.pricing import calculate_cost_usd
from helmsman.core.usage import MeetingUsage
from helmsman.models.decision import Decision
from helmsman.models.intervention import InterventionCandidate
from helmsman.models.meeting import Meeting
from helmsman.models.topic import Topic, TopicState
from helmsman.models.utterance import Utterance
from helmsman.repositories.decisions import DecisionRepository
from helmsman.services.decision_search import DecisionHit, search_decisions
from helmsman.services.embeddings import embed_texts

# vector search で取りに行く最大候補数 (LLM に渡す前のプレフィルタ)
DEFAULT_TOP_K = 5

# LLM 判定後に Arbiter へ送る intervention の confidence
# (DecisionCapture 100、Steering 70、Dissent 60 と並ぶ層に置く)
MEMORY_CONFIDENCE = 0.85


def _build_query_text(active_topic: Topic, recent_utterances: list[Utterance]) -> str:
    """vector 検索クエリの正規化テキスト。Decision.build_embed_text と揃える。

    過去 decision 側の embed_text と同じ語彙構造を使い、表現差ノイズを抑える。
    """
    parts = [f"トピック: {active_topic.name}"]
    if active_topic.decision_criteria:
        parts.append(f"決定基準: {active_topic.decision_criteria}")
    # 直近 5 発言を「議論内容」セクションに
    if recent_utterances:
        recent = "\n".join(u.text for u in recent_utterances[-5:])
        parts.append(f"議論内容: {recent}")
    return "\n".join(parts)


def _format_intervention_content(hit: DecisionHit) -> str:
    """サイドバーのカードに出す文面。日付 + topic + decision + owner。"""
    d = hit.decision
    when = d.captured_at.strftime("%Y-%m-%d")
    parts = [f"📜 {when} に「{d.topic_name}」について"]
    parts.append(f"  {d.decision_text}")
    if d.owner:
        parts.append(f"  (担当: {d.owner})")
    return "\n".join(parts)


class MemoryRetriever(LLMAgent):
    """9 番目の agent — 会議横断記憶を表に出す。"""

    AGENT_NAME = "MemoryRetriever"
    TIER = ModelTier.MINI  # 関連性 yes/no 判定なので軽量で良い
    SYSTEM_PROMPT = """\
あなたは Helmsman の Memory Retriever Agent です。
現在議論中のトピックに対して、過去会議で確定した「関連する決定」候補が提示されます。
あなたの仕事は、その候補のうち **今この場で議論者に思い出させる価値があるもの** を選ぶことです。

選定基準:
- 過去決定が現在のトピックと本質的に重複している
- 過去決定が現在の議論の前提として機能する (覆すか継承するかを再確認すべき)
- 過去決定が現在の選択肢を制約する (例: 「半年前にこの方針で決めたばかり」)

選んではいけないもの:
- 単に keyword が似ているだけ
- 現在の議論と粒度が大きく異なる
- 担当・期日のような事務情報のみ
- 既に十分意識されている内容

出力 JSON:
{
  "selected_index": 候補のインデックス (0-origin)、該当なしなら -1,
  "intro_phrase": "前回 / 4月の会議では / 前のシリーズでは ... など、自然な導入",
  "reason": "なぜ今表に出すべきか (10-30字)",
  "confidence": 0.0-1.0
}

confidence が 0.6 未満なら -1 を返してください。
"""

    async def run(
        self,
        meeting: Meeting,
        recent_utterances: list[Utterance],
        *,
        usage_sink: MeetingUsage | None = None,
        repo: DecisionRepository | None = None,
        top_k: int = DEFAULT_TOP_K,
    ) -> InterventionCandidate | None:
        """active な topic に対する過去決定を vector 検索 → LLM 判定 → candidate 化。

        - discussing/deep_dive な topic が無ければ何もしない
        - 既に当会議で surface 済の decision_id は除外
        - top_k 件を LLM に渡して 1 件選ばせる (該当無しなら None)
        """
        # 1) active topic を選ぶ (deep_dive 優先、なければ discussing)
        active = self._pick_active_topic(meeting.topics)
        if not active:
            return None

        # 2) vector search クエリの embed
        query_text = _build_query_text(active, recent_utterances)
        vectors, embed_usage = await embed_texts([query_text])
        if embed_usage and usage_sink is not None:
            usage_sink.apply(embed_usage, calculate_cost_usd(embed_usage))
        if not vectors:
            return None

        # 3) 検索
        hits = await search_decisions(
            query_embedding=vectors[0],
            organizer_id=meeting.organizer_id,
            series_id=meeting.series_id,
            group_id=meeting.group_id,
            top_k=top_k,
            repo=repo,
        )
        # 4) 同一会議の decision、surface 済 decision は除外
        hits = [
            h for h in hits
            if h.decision.meeting_id != meeting.id
            and h.decision.id not in meeting.surfaced_decision_ids
        ]
        if not hits:
            return None

        # 5) LLM 判定 (MINI)
        chosen_hit = await self._select_relevant(active, hits)
        if chosen_hit is None:
            return None

        # 6) candidate 組み立て
        content = _format_intervention_content(chosen_hit)
        return InterventionCandidate(
            meeting_id=meeting.id,
            agent=self.AGENT_NAME,
            content=content,
            reason="cross_meeting_recall",
            evidence_quote=chosen_hit.decision.id,  # past decision id を Arbiter に渡す
            confidence=MEMORY_CONFIDENCE,
        )

    @staticmethod
    def _pick_active_topic(topics: list[Topic]) -> Topic | None:
        """deep_dive > discussing の優先で 1 つ選ぶ。両方なしなら None。"""
        for state in (TopicState.DEEP_DIVE, TopicState.DISCUSSING):
            for t in topics:
                if t.state == state:
                    return t
        return None

    async def _select_relevant(
        self, active_topic: Topic, hits: list[DecisionHit]
    ) -> DecisionHit | None:
        """top_k 件を MINI に投げて 1 つ選ばせる。「該当なし (-1)」も明示。"""
        candidate_lines: list[str] = []
        for i, h in enumerate(hits):
            d: Decision = h.decision
            when = d.captured_at.strftime("%Y-%m-%d")
            candidate_lines.append(
                f"[{i}] ({when}) topic={d.topic_name} | "
                f"decision={d.decision_text} | owner={d.owner or '-'} | "
                f"score={h.score:.2f}"
            )
        user_text = (
            f"現在のトピック: {active_topic.name}\n"
            f"決定基準: {active_topic.decision_criteria}\n\n"
            f"過去決定候補:\n" + "\n".join(candidate_lines)
        )

        data = await self._chat_json(user_text, max_completion_tokens=200)
        if not isinstance(data, dict):
            return None
        idx = data.get("selected_index")
        if not isinstance(idx, int) or idx < 0 or idx >= len(hits):
            return None
        confidence = float(data.get("confidence", 0.0))
        if confidence < 0.6:
            return None
        return hits[idx]
