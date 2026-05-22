"""In-memory ring buffer for face signals (Phase 6)。

Cosmos に永続化はするが、EngagementAgent が tick で参照するのは「直近 5 分」の
シグナルだけなので、Cosmos query を毎 tick 走らせるより in-process buffer の方が
レイテンシ・コストとも有利。

Container App 再起動時は失われるが、Cosmos の永続化が source of truth として残るので
レポート生成や事後分析には影響しない (live agent だけが影響を受ける、許容)。

スレッドセーフ: asyncio.Lock で同期。複数 worker process があるとプロセス毎に
独立した buffer になる (現状の Container App は単一 process なので問題ない)。
"""
from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass

from helmsman.models.face_signal import FaceSignalBatch, FaceWindow

# 直近 5 分 = 75 windows (2 秒窓) を保持
DEFAULT_BUFFER_SIZE = 80


@dataclass
class ParticipantWindow:
    """meeting × participant 単位の集計 window 1 件 (server 時刻 + 参加者情報を付加)。"""

    participant_id: str
    window_start_ms: float
    nod_count: int
    confusion: float
    engagement: float
    face_visible_ratio: float
    server_received_at_ms: float


class FaceSignalBuffer:
    """meeting_id をキーに deque[ParticipantWindow] を保持する singleton。"""

    def __init__(self, max_size: int = DEFAULT_BUFFER_SIZE) -> None:
        self._buffers: dict[str, deque[ParticipantWindow]] = {}
        self._lock = asyncio.Lock()
        self._max_size = max_size

    async def append_batch(
        self, batch: FaceSignalBatch, server_received_at_ms: float
    ) -> None:
        """batch.windows を ParticipantWindow に変換して保存。"""
        async with self._lock:
            buf = self._buffers.setdefault(
                batch.meeting_id, deque(maxlen=self._max_size)
            )
            for w in batch.windows:
                buf.append(
                    ParticipantWindow(
                        participant_id=batch.participant_id,
                        window_start_ms=w.window_start_ms,
                        nod_count=w.nod_count,
                        confusion=w.confusion,
                        engagement=w.engagement,
                        face_visible_ratio=w.face_visible_ratio,
                        server_received_at_ms=server_received_at_ms,
                    )
                )

    async def recent(
        self, meeting_id: str, *, within_ms: float = 300_000
    ) -> list[ParticipantWindow]:
        """指定 meeting の直近 N ミリ秒の windows を新しい順に返す。"""
        async with self._lock:
            buf = self._buffers.get(meeting_id)
            if not buf:
                return []
            items = list(buf)
        if not items:
            return []
        # server_received_at_ms ベースで filter (client 時刻は drift する可能性)
        latest = max(it.server_received_at_ms for it in items)
        cutoff = latest - within_ms
        recent = [it for it in items if it.server_received_at_ms >= cutoff]
        recent.sort(key=lambda w: w.server_received_at_ms, reverse=True)
        return recent

    async def clear(self, meeting_id: str) -> None:
        """会議終了時のクリーンアップ。"""
        async with self._lock:
            self._buffers.pop(meeting_id, None)

    def stats(self) -> dict[str, int]:
        """buffer 健康診断 (debug 用、lock なし)。"""
        return {mid: len(buf) for mid, buf in self._buffers.items()}


# シングルトン (FastAPI 起動中保持される)
_buffer: FaceSignalBuffer | None = None


def get_face_signal_buffer() -> FaceSignalBuffer:
    global _buffer
    if _buffer is None:
        _buffer = FaceSignalBuffer()
    return _buffer


# ===== summary 計算 (EngagementAgent から呼ばれる) =====


@dataclass
class FaceSignalSummary:
    """直近 N 秒の集計 — EngagementAgent が pattern 判定に使う。"""

    sample_count: int  # window 数 (人数 × 2秒窓 数)
    participants: int  # ユニーク participant 数
    total_nods: int  # 合計うなずき回数
    mean_confusion: float  # 加重平均
    mean_engagement: float
    high_confusion_count: int  # confusion > 0.6 だった window 数
    low_engagement_count: int  # engagement < 0.4 だった window 数


def summarize_windows(
    windows: list[ParticipantWindow],
    *,
    high_confusion_threshold: float = 0.6,
    low_engagement_threshold: float = 0.4,
) -> FaceSignalSummary:
    """ParticipantWindow リスト → EngagementAgent 用の集計サマリ。"""
    if not windows:
        return FaceSignalSummary(
            sample_count=0,
            participants=0,
            total_nods=0,
            mean_confusion=0.0,
            mean_engagement=0.0,
            high_confusion_count=0,
            low_engagement_count=0,
        )
    return FaceSignalSummary(
        sample_count=len(windows),
        participants=len({w.participant_id for w in windows}),
        total_nods=sum(w.nod_count for w in windows),
        mean_confusion=sum(w.confusion for w in windows) / len(windows),
        mean_engagement=sum(w.engagement for w in windows) / len(windows),
        high_confusion_count=sum(
            1 for w in windows if w.confusion >= high_confusion_threshold
        ),
        low_engagement_count=sum(
            1 for w in windows if w.engagement <= low_engagement_threshold
        ),
    )
