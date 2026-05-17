"""シンプルな API キー認証 (dev / 審査用)。

本番では Entra ID トークン検証に置き換える前提。
"""
from __future__ import annotations

from fastapi import Header, HTTPException, status

from helmsman.core.config import get_settings


async def require_api_key(
    x_helmsman_key: str | None = Header(default=None, alias="X-Helmsman-Key"),
) -> None:
    """`HELMSMAN_REQUIRE_AUTH=true` のとき X-Helmsman-Key ヘッダーを必須にする。

    開発中は `HELMSMAN_REQUIRE_AUTH=false` (default) で素通り。
    審査員試用 URL では `HELMSMAN_REQUIRE_AUTH=true` + 共有キーで運用予定。
    """
    settings = get_settings()
    if not settings.helmsman_require_auth:
        return
    if not settings.helmsman_api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="HELMSMAN_REQUIRE_AUTH=true だが HELMSMAN_API_KEY が未設定",
        )
    if x_helmsman_key != settings.helmsman_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-Helmsman-Key ヘッダーが必須または不正",
        )
