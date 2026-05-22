"""Phase 6 — face_signal_buffer + summarize の単体テスト。

API endpoint はモジュール統合層なので test_api_smoke 系で別途検査。
"""
from __future__ import annotations

import asyncio

import pytest

from helmsman.models.face_signal import FaceSignalBatch, FaceWindow
from helmsman.services.face_signal_buffer import (
    FaceSignalBuffer,
    summarize_windows,
)


def _batch(
    *,
    meeting_id: str = "m1",
    participant_id: str = "p1",
    windows: list[FaceWindow] | None = None,
) -> FaceSignalBatch:
    return FaceSignalBatch(
        meeting_id=meeting_id,
        organizer_id="u1",
        participant_id=participant_id,
        windows=windows or [],
    )


def _window(
    *,
    start: float = 0.0,
    nods: int = 0,
    confusion: float = 0.0,
    engagement: float = 0.0,
    visible: float = 1.0,
    samples: int = 20,
) -> FaceWindow:
    return FaceWindow(
        window_start_ms=start,
        sample_count=samples,
        nod_count=nods,
        confusion=confusion,
        engagement=engagement,
        face_visible_ratio=visible,
    )


# ===== FaceSignalBuffer =====


@pytest.mark.asyncio
async def test_buffer_append_and_recent_returns_newest_first():
    buf = FaceSignalBuffer()
    await buf.append_batch(
        _batch(windows=[_window(start=0), _window(start=2000)]),
        server_received_at_ms=10_000,
    )
    await buf.append_batch(
        _batch(windows=[_window(start=4000)]),
        server_received_at_ms=14_000,
    )
    recent = await buf.recent("m1", within_ms=60_000)
    assert len(recent) == 3
    # 新しい順 (server_received_at_ms 降順)
    assert recent[0].server_received_at_ms >= recent[1].server_received_at_ms
    assert recent[-1].server_received_at_ms == 10_000


@pytest.mark.asyncio
async def test_buffer_recent_filters_by_within_ms():
    buf = FaceSignalBuffer()
    # 古い batch
    await buf.append_batch(
        _batch(windows=[_window(start=0)]),
        server_received_at_ms=1_000,
    )
    # 新しい batch (古い方から 100s 後)
    await buf.append_batch(
        _batch(windows=[_window(start=100_000)]),
        server_received_at_ms=101_000,
    )
    # within=10s だけ取ると、古い方は cutoff 外で除外
    recent = await buf.recent("m1", within_ms=10_000)
    assert len(recent) == 1
    assert recent[0].window_start_ms == 100_000


@pytest.mark.asyncio
async def test_buffer_per_meeting_isolation():
    buf = FaceSignalBuffer()
    await buf.append_batch(
        _batch(meeting_id="mA", windows=[_window(start=0)]),
        server_received_at_ms=1_000,
    )
    await buf.append_batch(
        _batch(meeting_id="mB", windows=[_window(start=0)]),
        server_received_at_ms=1_000,
    )
    assert len(await buf.recent("mA", within_ms=60_000)) == 1
    assert len(await buf.recent("mB", within_ms=60_000)) == 1
    assert len(await buf.recent("mC", within_ms=60_000)) == 0


@pytest.mark.asyncio
async def test_buffer_clear_drops_all_windows():
    buf = FaceSignalBuffer()
    await buf.append_batch(
        _batch(windows=[_window(start=0)]),
        server_received_at_ms=1_000,
    )
    await buf.clear("m1")
    assert await buf.recent("m1", within_ms=60_000) == []


@pytest.mark.asyncio
async def test_buffer_caps_at_max_size():
    buf = FaceSignalBuffer(max_size=3)
    for i in range(10):
        await buf.append_batch(
            _batch(windows=[_window(start=float(i * 1000))]),
            server_received_at_ms=float(i * 1000),
        )
    recent = await buf.recent("m1", within_ms=1_000_000)
    assert len(recent) == 3  # 古いものから捨てられる


@pytest.mark.asyncio
async def test_buffer_concurrent_appends_do_not_lose_data():
    """asyncio.Lock の sanity check — 並列 append で件数が落ちないか。"""
    buf = FaceSignalBuffer(max_size=100)

    async def push(i: int):
        await buf.append_batch(
            _batch(windows=[_window(start=float(i))]),
            server_received_at_ms=float(i),
        )

    await asyncio.gather(*(push(i) for i in range(50)))
    recent = await buf.recent("m1", within_ms=1_000_000)
    assert len(recent) == 50


# ===== summarize_windows =====


def test_summarize_empty_window_list():
    s = summarize_windows([])
    assert s.sample_count == 0
    assert s.participants == 0
    assert s.total_nods == 0


@pytest.mark.asyncio
async def test_summarize_counts_high_confusion_low_engagement():
    buf = FaceSignalBuffer()
    await buf.append_batch(
        _batch(
            participant_id="alice",
            windows=[
                _window(confusion=0.8, engagement=0.2),  # high conf, low eng
                _window(confusion=0.1, engagement=0.9),  # neither
            ],
        ),
        server_received_at_ms=1_000,
    )
    await buf.append_batch(
        _batch(
            participant_id="bob",
            windows=[_window(confusion=0.7, engagement=0.3, nods=3)],
        ),
        server_received_at_ms=2_000,
    )

    recent = await buf.recent("m1", within_ms=60_000)
    s = summarize_windows(recent)
    assert s.sample_count == 3
    assert s.participants == 2  # alice + bob
    assert s.total_nods == 3
    assert s.high_confusion_count == 2  # 0.8 と 0.7
    assert s.low_engagement_count == 2  # 0.2 と 0.3
    assert 0.0 < s.mean_confusion < 1.0


def test_summarize_threshold_customization():
    from helmsman.services.face_signal_buffer import ParticipantWindow

    windows = [
        ParticipantWindow(
            participant_id="a",
            window_start_ms=0,
            nod_count=0,
            confusion=0.5,
            engagement=0.5,
            face_visible_ratio=1.0,
            server_received_at_ms=0,
        )
    ]
    # デフォルト閾値 (0.6/0.4) では high/low に該当しない
    s_default = summarize_windows(windows)
    assert s_default.high_confusion_count == 0
    assert s_default.low_engagement_count == 0
    # 閾値を緩めると該当
    s_loose = summarize_windows(
        windows, high_confusion_threshold=0.4, low_engagement_threshold=0.6
    )
    assert s_loose.high_confusion_count == 1
    assert s_loose.low_engagement_count == 1


# ===== FaceSignalBatch helpers =====


def test_batch_total_nods_and_means():
    batch = _batch(
        windows=[
            _window(nods=2, confusion=0.3, engagement=0.7),
            _window(nods=3, confusion=0.5, engagement=0.5),
        ]
    )
    assert batch.total_nods == 5
    assert batch.mean_confusion == 0.4
    assert batch.mean_engagement == 0.6


def test_batch_empty_means_are_zero():
    batch = _batch()
    assert batch.total_nods == 0
    assert batch.mean_confusion == 0.0
    assert batch.mean_engagement == 0.0
