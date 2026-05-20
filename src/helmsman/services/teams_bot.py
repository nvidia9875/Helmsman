"""Teams 会議への bot 派遣のエントリポイント (薄いラッパ)。

2026-05-20 切替: ACS Call Automation の TeamsMeetingLinkLocator が公式 API/全 SDK に
存在しないと判明したため、Microsoft Graph Communications API ベースの実装に切替。

実装本体は `services/graph_calling.py`。このモジュールは旧 ACS 時代のシグネチャ
(`invite_bot_to_teams_meeting()`, `hangup_bot()`, `parse_operation_context()`,
`_build_operation_context()`) を維持して既存 API ルーターや tests が動き続けるようにする。
"""
from __future__ import annotations

from helmsman.services.graph_calling import (
    _build_operation_context,
    hangup_via_graph,
    join_meeting_via_graph,
    parse_operation_context,
)

# 旧 API 互換 (api/routers/bot.py や tests/ から import される)
__all__ = [
    "_build_operation_context",
    "hangup_bot",
    "invite_bot_to_teams_meeting",
    "parse_operation_context",
]


async def invite_bot_to_teams_meeting(
    *, meeting_id: str, organizer_id: str, teams_meeting_url: str
) -> str:
    """Teams 会議に Helmsman bot を参加させる (Graph Calling 経由)。

    Returns:
        Graph call ID — webhook の event でこの ID を見て meeting を引く

    Raises:
        RuntimeError: 設定不備
        httpx.HTTPStatusError: Graph API エラー (401/403/404 等)
    """
    return await join_meeting_via_graph(
        meeting_id=meeting_id,
        organizer_id=organizer_id,
        teams_meeting_url=teams_meeting_url,
    )


async def hangup_bot(call_id: str) -> None:
    """Bot を会議から退出させる (Graph DELETE /communications/calls/{id})。"""
    await hangup_via_graph(call_id)
