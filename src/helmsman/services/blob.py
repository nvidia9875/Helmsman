"""Azure Blob Storage 文書アップロード ラッパー。

dev 環境 (AZURE_STORAGE_CONNECTION_STRING 未設定) では NoOp に近い in-memory
モードで動作し、ローカルテストを止めない。本番では Azure Blob にアップロード。
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from helmsman.core.config import get_settings
from helmsman.core.logging import logger

CONTAINER_NAME = "documents"

# SAS URL の有効期限 (プレビュー / ダウンロード用)
SAS_EXPIRY_MINUTES = 15


def blob_path_for(owner_id: str, document_id: str, filename: str) -> str:
    """文書 1 件あたりの blob path。会議 ID or グループ ID で名前空間を分ける。"""
    return f"{owner_id}/{document_id}/{filename}"


async def upload_document_blob(
    *, owner_id: str, document_id: str, filename: str, data: bytes,
    content_type: str | None = None,
) -> str:
    """文書バイナリを Blob にアップロードし、blob_path を返す。

    AZURE_STORAGE_CONNECTION_STRING が未設定なら NoOp (path だけ返す)。
    """
    path = blob_path_for(owner_id, document_id, filename)
    settings = get_settings()
    if not settings.azure_storage_connection_string:
        logger.info("blob.skipped_no_config", path=path, size=len(data))
        return path

    # 遅延 import: Azure SDK 重いので使う時だけ
    from azure.storage.blob import ContentSettings
    from azure.storage.blob.aio import BlobServiceClient

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


async def delete_document_blob(*, blob_path: str) -> bool:
    """文書 Blob を削除。404 は True で吸収。Storage 未設定なら NoOp。"""
    settings = get_settings()
    if not settings.azure_storage_connection_string:
        logger.info("blob.delete_skipped_no_config", path=blob_path)
        return True

    from azure.core.exceptions import ResourceNotFoundError
    from azure.storage.blob.aio import BlobServiceClient

    async with BlobServiceClient.from_connection_string(
        settings.azure_storage_connection_string
    ) as service:
        blob = service.get_blob_client(container=CONTAINER_NAME, blob=blob_path)
        try:
            await blob.delete_blob()
        except ResourceNotFoundError:
            logger.info("blob.delete_not_found", path=blob_path)
            return True
    logger.info("blob.deleted", path=blob_path)
    return True


def generate_download_sas_url(*, blob_path: str) -> str | None:
    """短命の read-only SAS URL を生成。Storage 未設定なら None。

    Frontend がプレビュー / ダウンロードに使う想定。
    """
    settings = get_settings()
    if not settings.azure_storage_connection_string:
        return None

    from azure.storage.blob import (
        BlobSasPermissions,
        BlobServiceClient,
        generate_blob_sas,
    )

    # 接続文字列からアカウント名 / キーを抽出 (sync client 経由)
    service = BlobServiceClient.from_connection_string(
        settings.azure_storage_connection_string
    )
    account_name = service.account_name
    account_key = service.credential.account_key  # type: ignore[union-attr]
    if not account_name or not account_key:
        return None

    expires_on = datetime.now(UTC) + timedelta(minutes=SAS_EXPIRY_MINUTES)
    sas_token = generate_blob_sas(
        account_name=account_name,
        container_name=CONTAINER_NAME,
        blob_name=blob_path,
        account_key=account_key,
        permission=BlobSasPermissions(read=True),
        expiry=expires_on,
    )
    return (
        f"https://{account_name}.blob.core.windows.net/"
        f"{CONTAINER_NAME}/{blob_path}?{sas_token}"
    )
