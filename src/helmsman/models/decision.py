"""Decision — 会議で確定した意思決定の永続化モデル。

Cosmos `decisions` (partition: /organizer_id) に格納。
DecisionCapture が confidence ≥ 0.7 を出した瞬間に write-through で生成され、
未来の会議の MemoryRetriever が「あの時こう決めましたよね」のソースとして引く。

Decision id は `f"{meeting_id}:{topic_id}"` で deterministic に振り、
同一トピックが議論内で再合意された時は upsert で更新する (重複を作らない)。

embedding はベクトル検索用 (text-embedding-3-small = 1536 dim)。
AI Search 未デプロイ環境では numpy in-process cosine で代替する (ADR-104)。
"""
from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field


def _now_utc() -> datetime:
    return datetime.now(UTC)


class Decision(BaseModel):
    """会議で確定した決定 1 件。"""

    id: str  # f"{meeting_id}:{topic_id}" で deterministic
    organizer_id: str  # partition key
    meeting_id: str
    topic_id: str
    topic_name: str

    decision_text: str = Field(min_length=1, max_length=2000)
    owner: str = Field(default="", max_length=120)
    deadline: str = Field(default="", max_length=120)  # 自然言語 or ISO date
    evidence_quote: str | None = Field(default=None, max_length=2000)
    dissent: list[str] = Field(default_factory=list)

    # スコープ (MemoryRetriever のフィルタ/ブースト用)
    series_id: str | None = None
    group_id: str | None = None

    # ベクトル検索
    embedding: list[float] | None = None
    embed_text: str = Field(default="", max_length=4000)  # embedding の入力スナップショット

    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    captured_at: datetime = Field(default_factory=_now_utc)
    updated_at: datetime = Field(default_factory=_now_utc)

    @staticmethod
    def make_id(meeting_id: str, topic_id: str) -> str:
        """deterministic な ID 生成 (同一トピック再合意時の upsert キー)。"""
        return f"{meeting_id}:{topic_id}"

    @staticmethod
    def build_embed_text(
        *, topic_name: str, decision_text: str, owner: str, evidence_quote: str | None
    ) -> str:
        """embedding に投げる正規化テキスト。

        順序を固定して書くことで「同一トピックの僅かな表現差で別ベクトルになる」
        ノイズを抑える。MemoryRetriever 側 query テキストと同じ template を使う。
        """
        parts = [f"トピック: {topic_name}", f"決定: {decision_text}"]
        if owner:
            parts.append(f"担当: {owner}")
        if evidence_quote:
            parts.append(f"根拠: {evidence_quote}")
        return "\n".join(parts)

    def touch(self) -> None:
        """updated_at を現在時刻に進める。"""
        self.updated_at = _now_utc()
