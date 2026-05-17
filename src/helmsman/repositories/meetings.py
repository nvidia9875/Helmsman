"""Meeting repository — Cosmos `meetings` container."""
from __future__ import annotations

from azure.cosmos.aio import ContainerProxy
from azure.cosmos.exceptions import CosmosResourceNotFoundError

from helmsman.models.meeting import Meeting
from helmsman.repositories.cosmos import get_database


class MeetingRepository:
    CONTAINER = "meetings"

    def __init__(self) -> None:
        self._container: ContainerProxy | None = None

    async def _get_container(self) -> ContainerProxy:
        if self._container is None:
            self._container = get_database().get_container_client(self.CONTAINER)
        return self._container

    async def create(self, meeting: Meeting) -> Meeting:
        container = await self._get_container()
        item = meeting.model_dump(mode="json")
        await container.create_item(body=item)
        return meeting

    async def get(self, meeting_id: str, organizer_id: str) -> Meeting | None:
        container = await self._get_container()
        try:
            item = await container.read_item(
                item=meeting_id, partition_key=organizer_id
            )
            return Meeting.model_validate(item)
        except CosmosResourceNotFoundError:
            return None

    async def upsert(self, meeting: Meeting) -> Meeting:
        container = await self._get_container()
        item = meeting.model_dump(mode="json")
        await container.upsert_item(body=item)
        return meeting
