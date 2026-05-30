"""`_should_auto_hangup` の grace period + フラつきデバウンスのユニットテスト。

実会議で観測した「bot が参加~1秒後に自滅する」バグ (Graph /participants 通知の
部分スナップショット由来で human_count が一瞬 0 にフラつき即 hangup) の再発防止。
"""
from __future__ import annotations

import time

import pytest

from helmsman.api.routers import bot


@pytest.fixture(autouse=True)
def _clear_roster_state():
    """各テストでプロセスローカルな観測状態をリセットする。"""
    bot._call_roster_state.clear()
    yield
    bot._call_roster_state.clear()


@pytest.fixture
def fake_clock(monkeypatch):
    """time.time() を手動で進められるフェイククロックに差し替える。"""
    state = {"now": 1_000.0}
    monkeypatch.setattr(time, "time", lambda: state["now"])

    def advance(seconds: float) -> None:
        state["now"] += seconds

    return advance


def test_empty_meeting_within_grace_does_not_hangup(fake_clock):
    # Arrange / Act: human を一度も見ないまま grace period 内
    result = bot._should_auto_hangup("call-1", human_count=0)

    # Assert: 参加直後の roster ラグの可能性 → 保留
    assert result is False


def test_empty_meeting_past_grace_hangs_up(fake_clock):
    # Arrange: 最初の観測 (human 0)
    assert bot._should_auto_hangup("call-1", human_count=0) is False

    # Act: grace period 超過
    fake_clock(bot.HANGUP_GRACE_SEC + 1)

    # Assert: 誰も来ない空会議 → hangup
    assert bot._should_auto_hangup("call-1", human_count=0) is True


def test_human_present_never_hangs_up(fake_clock):
    # Arrange / Act
    result = bot._should_auto_hangup("call-1", human_count=1)

    # Assert: human が居る間は当然 hangup しない + 状態が更新される
    assert result is False
    assert bot._call_roster_state["call-1"]["human_seen"] is True
    assert bot._call_roster_state["call-1"]["last_human_at"] == time.time()


def test_momentary_zero_after_human_does_not_hangup(fake_clock):
    """本命: human を見た直後に 0 へフラついても即 hangup しない。"""
    # Arrange: human を観測
    assert bot._should_auto_hangup("call-1", human_count=1) is False

    # Act: 29ms 後に部分スナップショットで human_count=0
    fake_clock(0.029)

    # Assert: デバウンスにより保留 (= 自滅しない)
    assert bot._should_auto_hangup("call-1", human_count=0) is False


def test_sustained_zero_after_human_hangs_up(fake_clock):
    # Arrange: human を観測
    assert bot._should_auto_hangup("call-1", human_count=1) is False

    # Act: HANGUP_EMPTY_SEC 以上 0 が継続
    fake_clock(bot.HANGUP_EMPTY_SEC + 1)

    # Assert: 本当に全員退出 → hangup
    assert bot._should_auto_hangup("call-1", human_count=0) is True


def test_human_returning_resets_empty_debounce(fake_clock):
    # Arrange: human 観測 → 短い 0 → human 復帰
    assert bot._should_auto_hangup("call-1", human_count=1) is False
    fake_clock(5)
    assert bot._should_auto_hangup("call-1", human_count=0) is False
    fake_clock(5)
    assert bot._should_auto_hangup("call-1", human_count=2) is False  # 復帰で last_human_at 更新

    # Act: 復帰後にまた短い 0
    fake_clock(bot.HANGUP_EMPTY_SEC - 1)

    # Assert: last_human_at が更新されているので保留
    assert bot._should_auto_hangup("call-1", human_count=0) is False


def test_per_call_state_is_isolated(fake_clock):
    # Arrange: call-1 で human を観測
    assert bot._should_auto_hangup("call-1", human_count=1) is False

    # Act / Assert: 別 call は独立 (human 未観測なので grace 内は保留)
    assert bot._should_auto_hangup("call-2", human_count=0) is False
    fake_clock(bot.HANGUP_GRACE_SEC + 1)
    assert bot._should_auto_hangup("call-2", human_count=0) is True
