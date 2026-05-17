"""Document repository — Cosmos `documents` container."""
from __future__ import annotations

from azure.cosmos.aio import ContainerProxy
from azure.cosmos.exceptions import CosmosResourceNotFoundError

from helmsman.models.document import Document
from helmsman.repositories.cosmos import get_database


class DocumentRepository:
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
