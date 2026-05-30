"""Microsoft Graph Communications API で Helmsman bot を Teams 会議に参加させる。

ACS Call Automation の代替実装 (2026-05-20 切替)。Python から HTTP REST で
Graph API を直接叩く Service-hosted media bot。

公式パス: https://learn.microsoft.com/en-us/graph/api/application-post-calls

認証は 2 種類のトークンを使い分ける:
- **Bot Framework JWT**: `/communications/calls` 系の API を叩く時
  (audience=botframework.com)
- **Microsoft Graph token**: `/users/{id}/onlineMeetings` 等の通常 Graph API 用
  (audience=graph.microsoft.com)

依存:
- Application Access Policy が organizer user に grant 済 (PowerShell)
- Bot app に application permission `OnlineMeetings.ReadWrite.All` / `Calls.JoinGroupCall.All` /
  `Calls.AccessMedia.All` 等が admin consent 済
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import httpx

from helmsman.core.config import get_settings
from helmsman.core.logging import logger

GRAPH_API_BASE = "https://graph.microsoft.com/v1.0"

# Bot Framework JWT 認証用 (Graph Calling API の Authorization に使う)
BOT_AUTH_URL = "https://login.microsoftonline.com/botframework.com/oauth2/v2.0/token"
BOT_SCOPE = "https://api.botframework.com/.default"

# 通常の Graph API 認証用 (onlineMeetings の lookup 等に使う)
GRAPH_AUTH_URL_TEMPLATE = "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
GRAPH_SCOPE = "https://graph.microsoft.com/.default"

# 会議チャット投稿用 delegated scope。app-only では POST /chats/{id}/messages が
# 403 (Teamwork.Migrate.All required) になるため、refresh token から user 文脈の
# access token を取得して投稿する。
GRAPH_CHAT_SCOPE = "https://graph.microsoft.com/Chat.ReadWrite offline_access"


@dataclass
class _TokenCache:
    """Process-local token cache. expires_at は epoch 秒で 60s 余裕を持って更新。"""

    token: str | None = None
    expires_at: float = 0.0


_bot_token = _TokenCache()
_graph_token = _TokenCache()
_chat_token = _TokenCache()

# call_id → (meeting_id, organizer_id) のプロセスローカルマップ。
# Graph webhook で operationContext が echo back されない場合、call_id でこちらを引く。
# Container App の minReplicas=1 + 短時間 call なら process-local で十分。
# 永続化が必要なら Cosmos に column 足して find_by_call_id() を追加する。
_call_registry: dict[str, tuple[str, str]] = {}


def register_call(call_id: str, meeting_id: str, organizer_id: str) -> None:
    _call_registry[call_id] = (meeting_id, organizer_id)


def lookup_call(call_id: str) -> tuple[str | None, str | None]:
    """call_id から (meeting_id, organizer_id) を返す。未登録なら (None, None)。"""
    pair = _call_registry.get(call_id)
    if pair:
        return pair
    return None, None


def unregister_call(call_id: str) -> None:
    _call_registry.pop(call_id, None)


def is_configured() -> bool:
    s = get_settings()
    return bool(
        s.microsoft_app_id
        and s.microsoft_app_password
        and s.microsoft_app_tenant_id
        and s.microsoft_app_organizer_user_id
        and s.acs_callback_base_url  # callback URL を流用 (Container App の public FQDN)
    )


def _build_operation_context(meeting_id: str, organizer_id: str) -> str:
    """webhook で meeting を直引きできるよう ID を埋め込む (旧 ACS と同形式)。"""
    return f"meeting:{meeting_id}|org:{organizer_id}"


def parse_operation_context(ctx: str | None) -> tuple[str | None, str | None]:
    """webhook で受けた operation_context から (meeting_id, organizer_id) を取り出す。"""
    if not ctx:
        return None, None
    meeting_id: str | None = None
    organizer_id: str | None = None
    for part in ctx.split("|"):
        if part.startswith("meeting:"):
            meeting_id = part[len("meeting:") :] or None
        elif part.startswith("org:"):
            organizer_id = part[len("org:") :] or None
    return meeting_id, organizer_id


def _callback_url() -> str:
    s = get_settings()
    assert s.acs_callback_base_url
    return f"{s.acs_callback_base_url.rstrip('/')}{s.graph_callback_path}"


async def _fetch_bot_token() -> tuple[str, int]:
    """Bot Framework JWT を client_credentials で取得。"""
    s = get_settings()
    assert s.microsoft_app_id and s.microsoft_app_password
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            BOT_AUTH_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": s.microsoft_app_id,
                "client_secret": s.microsoft_app_password,
                "scope": BOT_SCOPE,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data["access_token"], int(data["expires_in"])


async def _fetch_graph_token() -> tuple[str, int]:
    """Microsoft Graph application token を client_credentials で取得。"""
    s = get_settings()
    assert s.microsoft_app_id and s.microsoft_app_password and s.microsoft_app_tenant_id
    url = GRAPH_AUTH_URL_TEMPLATE.format(tenant=s.microsoft_app_tenant_id)
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            url,
            data={
                "grant_type": "client_credentials",
                "client_id": s.microsoft_app_id,
                "client_secret": s.microsoft_app_password,
                "scope": GRAPH_SCOPE,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data["access_token"], int(data["expires_in"])


async def _fetch_chat_token() -> tuple[str, int]:
    """会議チャット投稿用 delegated access token を refresh token から取得。

    device code フローで取得した refresh token (admin@helmsmanjp 等の文脈) を使う。
    refresh token は rotation されないと仮定 (Azure AD はデフォルトで rotate するが、
    ここでは取得した access token だけキャッシュし、毎回 refresh token で更新する)。
    """
    s = get_settings()
    if not (
        s.microsoft_chat_refresh_token
        and s.microsoft_app_id
        and s.microsoft_app_tenant_id
    ):
        raise RuntimeError(
            "Chat delegated token not configured "
            "(MICROSOFT_CHAT_REFRESH_TOKEN / MICROSOFT_APP_ID / TENANT_ID)"
        )
    url = GRAPH_AUTH_URL_TEMPLATE.format(tenant=s.microsoft_app_tenant_id)
    # NOTE: device code で取った refresh token は public client 由来なので、
    # 交換時に client_secret を付けると AADSTS700025 で 401 になる。secret は付けない。
    data = {
        "grant_type": "refresh_token",
        "client_id": s.microsoft_app_id,
        "refresh_token": s.microsoft_chat_refresh_token,
        "scope": GRAPH_CHAT_SCOPE,
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(url, data=data)
        resp.raise_for_status()
        body = resp.json()
        return body["access_token"], int(body["expires_in"])


async def _get_token(cache: _TokenCache, fetcher) -> str:
    """キャッシュが有効ならそれを返す、無ければ取得。expiry 60s 前にリフレッシュ。"""
    now = time.time()
    if cache.token and cache.expires_at > now + 60:
        return cache.token
    token, expires_in = await fetcher()
    cache.token = token
    cache.expires_at = now + expires_in
    return token


async def get_bot_token() -> str:
    return await _get_token(_bot_token, _fetch_bot_token)


async def get_graph_token() -> str:
    return await _get_token(_graph_token, _fetch_graph_token)


async def get_chat_token() -> str:
    """会議チャット投稿用 delegated access token (refresh token 由来)。"""
    return await _get_token(_chat_token, _fetch_chat_token)


async def lookup_meeting_by_url(teams_meeting_url: str) -> dict[str, Any]:
    """Teams 会議 URL から onlineMeeting の詳細 (chatInfo, joinMeetingIdSettings 等) を取得。

    Application permission での `/users/{id}/onlineMeetings?$filter=JoinWebUrl eq ...` を使う。
    organizer は env 設定の `microsoft_app_organizer_user_id` を仮定。

    新形式 `/meet/<id>?p=<passcode>` URL でも joinWebUrl フィルタが効くかは
    実機検証が必要 (Microsoft が裏でクエリパラメタを正規化してくれる前提)。
    """
    s = get_settings()
    if not s.microsoft_app_organizer_user_id:
        raise RuntimeError("MICROSOFT_APP_ORGANIZER_USER_ID not configured")

    token = await get_graph_token()
    url = (
        f"{GRAPH_API_BASE}/users/{s.microsoft_app_organizer_user_id}/onlineMeetings"
    )
    # $filter 内のシングルクォートは値の囲みなので URL の中の ' は escape 不要だが安全のため
    safe_url = teams_meeting_url.replace("'", "''")
    params = {"$filter": f"JoinWebUrl eq '{safe_url}'"}

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(
            url,
            headers={"Authorization": f"Bearer {token}"},
            params=params,
        )
        if resp.status_code >= 400:
            logger.error(
                "graph.lookup_meeting_failed",
                status=resp.status_code,
                body=resp.text[:500],
                url=teams_meeting_url[:80],
            )
            resp.raise_for_status()
        data = resp.json()
        meetings = data.get("value", [])
        if not meetings:
            raise RuntimeError(
                f"No onlineMeeting found for URL "
                f"(organizer={s.microsoft_app_organizer_user_id[:8]}..., "
                f"url={teams_meeting_url[:60]}...)"
            )
        return meetings[0]


async def resolve_thread_id(teams_meeting_url: str) -> str | None:
    """Teams 会議 URL から会議チャットの threadId を解決(チャット投稿用)。"""
    try:
        meeting = await lookup_meeting_by_url(teams_meeting_url)
        chat_info = meeting.get("chatInfo") or {}
        return chat_info.get("threadId")
    except Exception as e:  # noqa: BLE001
        logger.error("graph.resolve_thread_failed", error=str(e)[:200])
        return None


async def post_meeting_chat_message(thread_id: str, html_content: str) -> bool:
    """会議チャット(threadId)に HTML メッセージを投稿する。

    Graph: POST /chats/{threadId}/messages。app-only では `ChatMessage.Send`
    (Teams の protected API)が必要。失敗しても例外は投げず False を返す
    (介入配信の本筋=音声/記録 を止めないため)。
    """
    try:
        # delegated token (user 文脈) で投稿。app-only では 403 になるため。
        token = await get_chat_token()
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{GRAPH_API_BASE}/chats/{thread_id}/messages",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json={"body": {"contentType": "html", "content": html_content}},
            )
        if resp.status_code >= 400:
            logger.error(
                "graph.chat_post_failed",
                status=resp.status_code,
                body=resp.text[:400],
                thread=thread_id[:40],
            )
            return False
        logger.info("graph.chat_posted", thread=thread_id[:40], chars=len(html_content))
        return True
    except Exception as e:  # noqa: BLE001
        logger.error("graph.chat_post_error", error=str(e)[:200])
        return False


async def join_meeting_via_graph(
    *,
    meeting_id: str,
    organizer_id: str,
    teams_meeting_url: str,
) -> str:
    """Graph Communications API で Teams 会議に bot を参加させる。

    Returns:
        Graph 側の call id (`/communications/calls/{id}` で参照)

    Raises:
        RuntimeError: 設定不備
        httpx.HTTPStatusError: Graph API エラー
    """
    if not is_configured():
        raise RuntimeError(
            "Graph Calling not configured (MICROSOFT_APP_* / acs_callback_base_url)"
        )

    s = get_settings()
    assert s.microsoft_app_tenant_id and s.microsoft_app_organizer_user_id

    # 1. 会議のメタデータを取得
    meeting = await lookup_meeting_by_url(teams_meeting_url)
    chat_info = meeting.get("chatInfo")
    if not chat_info or not chat_info.get("threadId"):
        raise RuntimeError("Meeting lacks chatInfo.threadId (cannot join via Graph)")

    # 2. Graph token を取得 (roles に Calls.* permissions が入ったやつ)
    # NOTE: Bot Framework JWT は audience=api.botframework.com で roles=[] のため
    # /communications/calls には使えない。Graph token (audience=graph.microsoft.com) が正解。
    graph_token = await get_graph_token()

    # 3. POST /communications/calls
    operation_context = _build_operation_context(meeting_id, organizer_id)
    payload: dict[str, Any] = {
        "@odata.type": "#microsoft.graph.call",
        "callbackUri": _callback_url(),
        "requestedModalities": ["audio"],
        "mediaConfig": {
            "@odata.type": "#microsoft.graph.serviceHostedMediaConfig"
        },
        "tenantId": s.microsoft_app_tenant_id,
        "chatInfo": {
            "@odata.type": "#microsoft.graph.chatInfo",
            "threadId": chat_info["threadId"],
            "messageId": chat_info.get("messageId", "0"),
        },
        "meetingInfo": {
            "@odata.type": "#microsoft.graph.organizerMeetingInfo",
            "organizer": {
                "@odata.type": "#microsoft.graph.identitySet",
                "user": {
                    "@odata.type": "#microsoft.graph.identity",
                    "id": s.microsoft_app_organizer_user_id,
                    "tenantId": s.microsoft_app_tenant_id,
                },
            },
            "allowConversationWithoutHost": True,
        },
        "operationContext": operation_context,
    }
    # reply chain がある場合は引き継ぐ (任意)
    if chat_info.get("replyChainMessageId"):
        payload["chatInfo"]["replyChainMessageId"] = chat_info[
            "replyChainMessageId"
        ]

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{GRAPH_API_BASE}/communications/calls",
            headers={
                "Authorization": f"Bearer {graph_token}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        if resp.status_code >= 400:
            logger.error(
                "graph.create_call_failed",
                status=resp.status_code,
                body=resp.text[:500],
                meeting_id=meeting_id,
            )
            resp.raise_for_status()
        data = resp.json()
        call_id = data["id"]
        # webhook で operationContext が落ちることがあるので、call_id ↔ meeting マップに登録
        register_call(call_id, meeting_id, organizer_id)
        logger.info(
            "graph.call_created",
            call_id=call_id,
            meeting_id=meeting_id,
            teams_meeting_url=teams_meeting_url[:80],
        )
        return call_id


async def hangup_via_graph(call_id: str) -> None:
    """Bot を会議から退出させる (DELETE /communications/calls/{id})。"""
    if not is_configured():
        return
    graph_token = await get_graph_token()
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.delete(
            f"{GRAPH_API_BASE}/communications/calls/{call_id}",
            headers={"Authorization": f"Bearer {graph_token}"},
        )
        # 404 は既に消えてる扱いで OK
        if resp.status_code not in (200, 202, 204, 404):
            logger.warning(
                "graph.hangup_unexpected",
                status=resp.status_code,
                body=resp.text[:200],
                call_id=call_id,
            )
        else:
            logger.info("graph.call_hung_up", call_id=call_id, status=resp.status_code)
