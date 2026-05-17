"""Group repository — Cosmos `groups` container (partition /organizer_id)."""
from __future__ import annotations

from azure.cosmos.aio import ContainerProxy
from azure.cosmos.exceptions import CosmosResourceNotFoundError

from helmsman.models.group import MeetingGroup
from helmsman.repositories.cosmos import get_database


class GroupRepository:
    CONTAINER = "groups"

    def __init__(self) -> None:
        self._container: ContainerProxy | None = None

    async def _get_container(self) -> ContainerProxy:
        if self._container is None:
            self._container = get_database().get_container_client(self.CONTAINER)
        return self._container

    async def create(self, group: MeetingGroup) -> MeetingGroup:
        container = await self._get_container()
        await container.create_item(body=group.model_dump(mode="json"))
        return group

    async def get(self, group_id: str, organizer_id: str) -> MeetingGroup | None:
        container = await self._get_container()
        try:
            item = await container.read_item(
                item=group_id, partition_key=organizer_id
            )
            return MeetingGroup.model_validate(item)
        except CosmosResourceNotFoundError:
            return None

    async def upsert(self, group: MeetingGroup) -> MeetingGroup:
        group.touch()
        container = await self._get_container()
        await container.upsert_item(body=group.model_dump(mode="json"))
        return group

    async def delete(self, group_id: str, organizer_id: str) -> bool:
        container = await self._get_container()
        try:
            await container.delete_item(item=group_id, partition_key=organizer_id)
            return True
        except CosmosResourceNotFoundError:
            return False

    async def list_by_organizer(
        self, organizer_id: str, limit: int = 50
    ) -> list[MeetingGroup]:
        """主催者のグループ一覧 (最近更新順)。partition 内クエリで cheap。"""
        container = await self._get_container()
        query = (
            "SELECT * FROM c WHERE c.organizer_id = @oid "
            "ORDER BY c.updated_at DESC OFFSET 0 LIMIT @lim"
        )
        params = [
            {"name": "@oid", "value": organizer_id},
            {"name": "@lim", "value": limit},
        ]
        items: list[MeetingGroup] = []
        async for raw in container.query_items(
            query=query, parameters=params, partition_key=organizer_id
        ):
            items.append(MeetingGroup.model_validate(raw))
        return items
