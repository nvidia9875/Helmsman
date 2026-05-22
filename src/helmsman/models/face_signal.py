"""FaceSignal — Phase 6 (マルチモーダル) のクライアント由来集計シグナル。

ブラウザ MediaPipe FaceLandmarker が 10Hz でランドマークを取り、2 秒窓で
集計したものを 4 秒 batch で POST してくる (ADR-105)。生フレームは送信しない、
集計値だけ。Cosmos `face_signals` (partition /meeting_id) に TTL 30 日で格納。

Privacy 原則 (ADR-107):
  - opt-in、デフォルト OFF
  - 集計値のみ (raw blendshape vector は受け取らない)
  - 30 日後に自動削除 (Cosmos TTL もしくは batch cleanup)
"""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from pydantic import BaseModel, Field


class FaceWindow(BaseModel):
    """2 秒窓の集計シグナル 1 件 — client/lib/face/detectors.ts と shape を合わせる。"""

    window_start_ms: float = Field(..., description="performance.now() 基準 (相対時刻)")
    sample_count: int = Field(default=0, ge=0)
    nod_count: int = Field(default=0, ge=0)
    confusion: float = Field(default=0.0, ge=0.0, le=1.0)
    engagement: float = Field(default=0.0, ge=0.0, le=1.0)
    face_visible_ratio: float = Field(default=0.0, ge=0.0, le=1.0)


class FaceSignalBatch(BaseModel):
    """4 秒間隔の batch upload — 通常 2 windows / batch。"""

    id: str = Field(default_factory=lambda: str(uuid4()))
    meeting_id: str  # partition key
    organizer_id: str
    participant_id: str  # 当面 organizer 自身 = userId、将来は多人数対応
    received_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    # クライアント時刻 (デバッグ用)
    client_sent_at_ms: float | None = None
    windows: list[FaceWindow] = Field(default_factory=list, max_length=20)

    @property
    def total_nods(self) -> int:
        return sum(w.nod_count for w in self.windows)

    @property
    def mean_confusion(self) -> float:
        if not self.windows:
            return 0.0
        return sum(w.confusion for w in self.windows) / len(self.windows)

    @property
    def mean_engagement(self) -> float:
        if not self.windows:
            return 0.0
        return sum(w.engagement for w in self.windows) / len(self.windows)
