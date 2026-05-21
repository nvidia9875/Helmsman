"""FastAPI smoke / integration tests.

Verifies the app boots, routes mount, and the new dispatch-mode meeting flow
(`POST /meetings` with optional teams_meeting_url + optional goal) works
end-to-end with mocked Cosmos + LLM dependencies.
"""
from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client() -> TestClient:
    from helmsman.api.main import app

    return TestClient(app)


@pytest.fixture
def mock_repo(monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
    """全 MeetingRepository インスタンスを AsyncMock 化。"""
    from helmsman.models.meeting import Meeting

    repo = AsyncMock()

    async def _create(meeting: Meeting) -> Meeting:
        return meeting

    async def _upsert(meeting: Meeting) -> Meeting:
        return meeting

    async def _get(meeting_id: str, organizer_id: str) -> Meeting | None:
        return None

    async def _list_by_organizer(organizer_id: str, limit: int = 20):
        return []

    repo.create.side_effect = _create
    repo.upsert.side_effect = _upsert
    repo.get.side_effect = _get
    repo.list_by_organizer.side_effect = _list_by_organizer

    def factory() -> Any:
        return repo

    monkeypatch.setattr(
        "helmsman.api.routers.meetings.MeetingRepository", factory
    )
    return repo


@pytest.fixture
def mock_goal_decomposer(monkeypatch: pytest.MonkeyPatch) -> None:
    """GoalDecomposer.run を mock してネットワーク呼び出しを避ける。"""
    from helmsman.agents.goal_decomposer import GoalDecomposer
    from helmsman.models.topic import Topic, TopicPriority

    async def fake_run(self: Any, goal: str, mode: Any, **_kw):
        return [
            Topic(
                name="技術完成度",
                decision_criteria="P0 0",
                time_budget_pct=50,
                priority=TopicPriority.CRITICAL,
            ),
            Topic(
                name="マーケ準備",
                decision_criteria="LP 公開",
                time_budget_pct=50,
                priority=TopicPriority.IMPORTANT,
            ),
        ]

    monkeypatch.setattr(GoalDecomposer, "run", fake_run)


# ===== Basic plumbing =====


def test_root_returns_service_info(client: TestClient) -> None:
    r = client.get("/")
    assert r.status_code == 200
    body = r.json()
    assert body["service"] == "helmsman"
    assert "/docs" in body["docs"]


def test_health(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_openapi_lists_dispatch_and_bot_routes(client: TestClient) -> None:
    r = client.get("/openapi.json")
    assert r.status_code == 200
    paths = r.json()["paths"]
    # 主要エンドポイントが mount されている
    assert "/meetings" in paths
    assert "/meetings/{meeting_id}" in paths
    assert "/meetings/{meeting_id}/tick" in paths
    assert "/meetings/{meeting_id}/usage" in paths
    assert "/meetings/{meeting_id}/redecompose" in paths
    assert "/meetings/{meeting_id}/bot/invite" in paths
    assert "/meetings/{meeting_id}/bot/leave" in paths
    assert "/meetings/{meeting_id}/bot/speak" in paths
    assert "/meetings/{meeting_id}/bot/transcript" in paths
    assert "/meetings/usage/summary" in paths
    # /api/calling は Graph Communications webhook (旧 ACS /bot/callback の代替)
    assert "/api/calling" in paths


# ===== Dispatch flow =====


def test_dispatch_with_goal_creates_meeting_with_topics(
    client: TestClient, mock_repo: AsyncMock, mock_goal_decomposer: None
) -> None:
    r = client.post(
        "/meetings",
        json={
            "organizer_id": "u-1",
            "goal": "β 版ローンチ可否を決定する",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["goal"] == "β 版ローンチ可否を決定する"
    assert len(body["topics"]) == 2  # mock_goal_decomposer の返り値
    assert body["bot_status"] == "idle"
    assert body["teams_meeting_url"] is None
    mock_repo.create.assert_awaited()


def test_dispatch_without_goal_skips_decomposition(
    client: TestClient, mock_repo: AsyncMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """ゴール空 = "監視のみ" モード = GoalDecomposer 呼ばれない。"""
    from helmsman.agents.goal_decomposer import GoalDecomposer

    called = {"n": 0}

    async def fake_run(*args, **kwargs):
        called["n"] += 1
        return []

    monkeypatch.setattr(GoalDecomposer, "run", fake_run)

    r = client.post(
        "/meetings",
        json={"organizer_id": "u-1", "goal": ""},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["topics"] == []
    assert called["n"] == 0


def test_dispatch_with_teams_url_invokes_bot_invite(
    client: TestClient,
    mock_repo: AsyncMock,
    mock_goal_decomposer: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """teams_meeting_url 指定 → invite_bot_to_teams_meeting が呼ばれ
    bot_status が connecting に。"""
    invited = {"calls": 0, "url": None}

    async def fake_invite(*, meeting_id, organizer_id, teams_meeting_url):
        invited["calls"] += 1
        invited["url"] = teams_meeting_url
        return "call-conn-123"

    monkeypatch.setattr(
        "helmsman.services.teams_bot.invite_bot_to_teams_meeting",
        fake_invite,
    )

    teams_url = "https://teams.microsoft.com/l/meetup-join/19%3ameeting/0123"
    r = client.post(
        "/meetings",
        json={
            "organizer_id": "u-1",
            "goal": "進捗確認",
            "teams_meeting_url": teams_url,
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["teams_meeting_url"] == teams_url
    assert body["bot_status"] == "connecting"
    assert body["bot_call_connection_id"] == "call-conn-123"
    assert invited["calls"] == 1


def test_dispatch_bot_invite_failure_marks_failed_but_still_201(
    client: TestClient,
    mock_repo: AsyncMock,
    mock_goal_decomposer: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Bot 派遣失敗時は会議は作成済 + bot_status=failed。HTTP 201 を維持。"""

    async def fake_invite(**_kw):
        raise RuntimeError("ACS not configured")

    monkeypatch.setattr(
        "helmsman.services.teams_bot.invite_bot_to_teams_meeting",
        fake_invite,
    )

    r = client.post(
        "/meetings",
        json={
            "organizer_id": "u-1",
            "goal": "g",
            "teams_meeting_url": "https://teams.microsoft.com/l/meetup-join/xxx",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["bot_status"] == "failed"


# ===== Auth / CORS smoke =====


def test_health_does_not_require_auth(client: TestClient) -> None:
    """/health はメッシュ監視で叩く想定 = 認証なし。"""
    r = client.get("/health")
    assert r.status_code == 200
