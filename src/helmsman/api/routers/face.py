"""Face signals API (Phase 6) — クライアント webcam の集計シグナル受信 + 読み出し。

POST /meetings/{id}/face-signals: クライアントが 4 秒ごとに batch 送信
GET  /meetings/{id}/face-signals/recent: UI ライブバッジが直近 5 分を polling
"""
from __future__ import annotations

import time

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from helmsman.api.security import require_api_key
from helmsman.core.logging import logger
from helmsman.models.face_signal import FaceSignalBatch
from helmsman.repositories.face_signals import FaceSignalRepository
from helmsman.repositories.meetings import MeetingRepository
from helmsman.services.face_signal_buffer import (
    FaceSignalSummary,
    get_face_signal_buffer,
    summarize_windows,
)

router = APIRouter(
    prefix="/meetings",
    tags=["face-signals"],
    dependencies=[Depends(require_api_key)],
)


class FaceSignalAcceptResponse(BaseModel):
    """送信受理レスポンス — 受け入れ件数のみ返す (echo はしない、軽量に)。"""

    accepted: bool
    windows_received: int
    buffered_count: int


class FaceSignalRecentResponse(BaseModel):
    """ライブバッジ用 — UI 1 リクエストで「今どんな状況か」が分かる粒度。"""

    summary: FaceSignalSummary
    within_ms: float


@router.post(
    "/{meeting_id}/face-signals",
    response_model=FaceSignalAcceptResponse,
)
async def ingest_face_signals(
    meeting_id: str,
    organizer_id: str,
    batch: FaceSignalBatch,
    persist: bool = True,
) -> FaceSignalAcceptResponse:
    """ブラウザクライアントが 4 秒ごとに windows を batch 送信する。

    - in-memory ring buffer に追加 (EngagementAgent はこっちを読む)
    - persist=True なら Cosmos にも 1 件 batch 保存 (事後分析用)

    URL の meeting_id と batch.meeting_id の整合性チェックを行う。
    """
    if batch.meeting_id != meeting_id:
        raise HTTPException(
            400,
            f"batch.meeting_id ({batch.meeting_id}) does not match URL ({meeting_id})",
        )

    # organizer 確認 (権限チェック軽量、prod では Entra ID JWT 推奨)
    meeting = await MeetingRepository().get(meeting_id, organizer_id)
    if meeting is None:
        raise HTTPException(404, "meeting not found")

    # batch.organizer_id を URL の organizer_id に揃える (クライアント信用しない)
    batch.organizer_id = organizer_id

    buf = get_face_signal_buffer()
    server_now_ms = time.time() * 1000.0
    await buf.append_batch(batch, server_received_at_ms=server_now_ms)

    if persist and batch.windows:
        try:
            await FaceSignalRepository().create(batch)
        except Exception as e:  # noqa: BLE001
            logger.warning("face.persist_failed", error=str(e), meeting_id=meeting_id)
            # 永続化失敗してもリアルタイム機能は維持

    stats = buf.stats()
    return FaceSignalAcceptResponse(
        accepted=True,
        windows_received=len(batch.windows),
        buffered_count=stats.get(meeting_id, 0),
    )


@router.get(
    "/{meeting_id}/face-signals/recent",
    response_model=FaceSignalRecentResponse,
)
async def get_recent_face_signals(
    meeting_id: str,
    organizer_id: str,
    within_ms: float = 300_000,
) -> FaceSignalRecentResponse:
    """サイドバーのライブバッジ用 — buffer から直近 N ms を集計して返す。"""
    # within_ms は 30 秒 ~ 30 分にクランプ
    within_ms = max(30_000.0, min(1_800_000.0, within_ms))

    meeting = await MeetingRepository().get(meeting_id, organizer_id)
    if meeting is None:
        raise HTTPException(404, "meeting not found")

    buf = get_face_signal_buffer()
    windows = await buf.recent(meeting_id, within_ms=within_ms)
    summary = summarize_windows(windows)
    return FaceSignalRecentResponse(summary=summary, within_ms=within_ms)
