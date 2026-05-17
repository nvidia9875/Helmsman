"""ACS Call Automation で Helmsman bot を Teams 会議に参加させる。

外部依存:
- Azure Communication Services リソース (Bicep で provision 済)
- Teams 会議 URL (paid Teams テナントが必須。Teams Free / personal は interop 不可)

Bot のアイデンティティは ACS 側 (Bot Framework 不要)。Teams 会議内では
"External" suffix 付きで参加者リストに表示される。
"""
from __future__ import annotations

from helmsman.core.config import get_settings
from helmsman.core.logging import logger


def _is_configured() -> bool:
    s = get_settings()
    return bool(s.acs_connection_string and s.acs_callback_base_url)


def _callback_url() -> str:
    s = get_settings()
    assert s.acs_callback_base_url
    return f"{s.acs_callback_base_url.rstrip('/')}{s.acs_callback_path}"


def _build_operation_context(meeting_id: str, organizer_id: str) -> str:
    """webhook で meeting を partition-key 直引きできるよう、両方の ID を埋め込む。

    フォーマット: `meeting:{meeting_id}|org:{organizer_id}`
    """
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


async def invite_bot_to_teams_meeting(
    *, meeting_id: str, organizer_id: str, teams_meeting_url: str
) -> str:
    """Teams 会議に Helmsman bot を参加させる。

    Returns:
        call_connection_id — webhook の event でこの ID を見て meeting を引く

    Raises:
        RuntimeError: ACS 未設定 or join 失敗
    """
    if not _is_configured():
        raise RuntimeError(
            "ACS not configured (ACS_CONNECTION_STRING / ACS_CALLBACK_BASE_URL)"
        )

    # 遅延 import — SDK が重い + dev 環境で必要なら入れる
    from azure.communication.callautomation.aio import CallAutomationClient
    from azure.communication.callautomation import TeamsMeetingLinkLocator

    settings = get_settings()
    assert settings.acs_connection_string

    operation_context = _build_operation_context(meeting_id, organizer_id)

    # Media streaming WebSocket: ACS は wss:// 経由で raw PCM を流してくる + 双方向 (Phase C で TTS in)
    # path に meeting_id と organizer_id を含めて、ハンドラ側で session を引けるようにする
    cb_base = settings.acs_callback_base_url
    assert cb_base
    media_ws_url = cb_base.replace("https://", "wss://").replace("http://", "ws://")
    media_ws_url = (
        f"{media_ws_url.rstrip('/')}/bot/media-stream/{meeting_id}/{organizer_id}"
    )

    from azure.communication.callautomation import (
        MediaStreamingAudioChannelType,
        MediaStreamingContentType,
        MediaStreamingOptions,
        StreamingTransportType,
    )

    media_options = MediaStreamingOptions(
        transport_url=media_ws_url,
        transport_type=StreamingTransportType.WEBSOCKET,
        content_type=MediaStreamingContentType.AUDIO,
        audio_channel_type=MediaStreamingAudioChannelType.MIXED,
        start_media_streaming=True,
        enable_bidirectional=True,  # Phase C で TTS を会議に流すために必要
    )

    async with CallAutomationClient.from_connection_string(
        settings.acs_connection_string
    ) as client:
        locator = TeamsMeetingLinkLocator(meeting_link=teams_meeting_url)
        result = await client.connect_call(
            call_locator=locator,
            callback_url=_callback_url(),
            operation_context=operation_context,
            media_streaming=media_options,
        )
        connection_id = result.call_connection_id
        logger.info(
            "bot.invited",
            meeting_id=meeting_id,
            call_connection_id=connection_id,
            teams_meeting_url=teams_meeting_url[:80],
            media_ws=media_ws_url,
        )
        return connection_id


async def hangup_bot(call_connection_id: str) -> None:
    """Bot を会議から退出させる (call を hang up)。"""
    if not _is_configured():
        return
    from azure.communication.callautomation.aio import CallAutomationClient

    settings = get_settings()
    assert settings.acs_connection_string

    async with CallAutomationClient.from_connection_string(
        settings.acs_connection_string
    ) as client:
        connection = client.get_call_connection(call_connection_id)
        try:
            await connection.hang_up(is_for_everyone=False)
            logger.info("bot.hung_up", call_connection_id=call_connection_id)
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "bot.hangup_failed",
                call_connection_id=call_connection_id,
                error=str(e),
            )
