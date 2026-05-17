"""Document repositories — Cosmos `documents` / `group_documents` コンテナ。

文書は 2 つの partition で持つ:
  - documents (partition /meeting_id) : 会議スコープ
  - group_documents (partition /group_id) : グループスコープ
モデルは同じ Document を使うが scope フィールドで識別する。
"""
from __future__ import annotations

from azure.cosmos.aio import ContainerProxy
from azure.cosmos.exceptions import CosmosResourceNotFoundError

from helmsman.models.document import Document, DocumentScope
from helmsman.repositories.cosmos import get_database


class DocumentRepository:
    """会議スコープの Document リポジトリ。partition=meeting_id。"""

    CONTAINER = "documents"

    def __init__(self) -> None:
        self._container: ContainerProxy | None = None

    async def _get_container(self) -> ContainerProxy:
        if self._container is None:
            self._container = get_database().get_container_client(self.CONTAINER)
        return self._container

    async def create(self, document: Document) -> Document:
        container = await self._get_container()
        await container.create_item(body=document.model_dump(mode="json"))
        return document

    async def get(self, document_id: str, meeting_id: str) -> Document | None:
        container = await self._get_container()
        try:
            item = await container.read_item(
                item=document_id, partition_key=meeting_id
            )
            return Document.model_validate(item)
        except CosmosResourceNotFoundError:
            return None

    async def upsert(self, document: Document) -> Document:
        container = await self._get_container()
        await container.upsert_item(body=document.model_dump(mode="json"))
        return document

    async def delete(self, document_id: str, meeting_id: str) -> bool:
        container = await self._get_container()
        try:
            await container.delete_item(item=document_id, partition_key=meeting_id)
            return True
        except CosmosResourceNotFoundError:
            return False

    async def list_by_meeting(self, meeting_id: str) -> list[Document]:
        """会議 1 件に紐付く文書一覧 (アップロード新しい順)。"""
        container = await self._get_container()
        query = (
            "SELECT * FROM c WHERE c.meeting_id = @mid "
            "ORDER BY c.uploaded_at DESC"
        )
        params = [{"name": "@mid", "value": meeting_id}]
        items: list[Document] = []
        async for raw in container.query_items(
            query=query, parameters=params, partition_key=meeting_id
        ):
            items.append(Document.model_validate(raw))
        return items


class GroupDocumentRepository:
    """グループスコープの Document リポジトリ。partition=group_id。

    モデルは同じ Document (scope=GROUP) を使うが、コンテナを分けることで
    会議 RAG と group RAG の filter が混線しないようにする。
    """

    CONTAINER = "group_documents"

    def __init__(self) -> None:
        self._container: ContainerProxy | None = None

    async def _get_container(self) -> ContainerProxy:
        if self._container is None:
            self._container = get_database().get_container_client(self.CONTAINER)
        return self._container

    async def create(self, document: Document) -> Document:
        if document.scope != DocumentScope.GROUP:
            raise ValueError("GroupDocumentRepository requires scope=GROUP")
        container = await self._get_container()
        await container.create_item(body=document.model_dump(mode="json"))
        return document

    async def get(self, document_id: str, group_id: str) -> Document | None:
        container = await self._get_container()
        try:
            item = await container.read_item(
                item=document_id, partition_key=group_id
            )
            return Document.model_validate(item)
        except CosmosResourceNotFoundError:
            return None

    async def upsert(self, document: Document) -> Document:
        container = await self._get_container()
        await container.upsert_item(body=document.model_dump(mode="json"))
        return document

    async def delete(self, document_id: str, group_id: str) -> bool:
        container = await self._get_container()
        try:
            await container.delete_item(item=document_id, partition_key=group_id)
            return True
        except CosmosResourceNotFoundError:
            return False

    async def list_by_group(self, group_id: str) -> list[Document]:
        """グループ 1 件に紐付く文書一覧 (新しい順)。"""
        container = await self._get_container()
        query = (
            "SELECT * FROM c WHERE c.group_id = @gid "
            "ORDER BY c.uploaded_at DESC"
        )
        params = [{"name": "@gid", "value": group_id}]
        items: list[Document] = []
        async for raw in container.query_items(
            query=query, parameters=params, partition_key=group_id
        ):
            items.append(Document.model_validate(raw))
        return items
