"""Azure Blob Storage 文書アップロード ラッパー。

dev 環境 (AZURE_STORAGE_CONNECTION_STRING 未設定) では NoOp に近い in-memory
モードで動作し、ローカルテストを止めない。本番では Azure Blob にアップロード。
"""
from __future__ import annotations

from helmsman.core.config import get_settings
from helmsman.core.logging import logger

CONTAINER_NAME = "documents"


def blob_path_for(meeting_id: str, document_id: str, filename: str) -> str:
    """文書 1 件あたりの blob path。会議 ID で名前空間を分ける。"""
    return f"{meeting_id}/{document_id}/{filename}"


async def upload_document_blob(
    *, meeting_id: str, document_id: str, filename: str, data: bytes,
    content_type: str | None = None,
) -> str:
    """文書バイナリを Blob にアップロードし、blob_path を返す。

    AZURE_STORAGE_CONNECTION_STRING が未設定なら NoOp (path だけ返す)。
    """
    path = blob_path_for(meeting_id, document_id, filename)
    settings = get_settings()
    if not settings.azure_storage_connection_string:
        logger.info("blob.skipped_no_config", path=path, size=len(data))
        return path

    # 遅延 import: Azure SDK 重いので使う時だけ
    from azure.storage.blob.aio import BlobServiceClient
    from azure.storage.blob import ContentSettings

    async with BlobServiceClient.from_connection_string(
        settings.azure_storage_connection_string
    ) as service:
        container = service.get_container_client(CONTAINER_NAME)
        # コンテナは Bicep で作成済前提。なければ create_container を呼ぶ
        blob = container.get_blob_client(path)
        await blob.upload_blob(
            data,
            overwrite=True,
            content_settings=ContentSettings(content_type=content_type)
            if content_type else None,
        )
    logger.info("blob.uploaded", path=path, size=len(data))
    return path
