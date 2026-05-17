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

    async def list_by_organizer(
        self, organizer_id: str, limit: int = 20
    ) -> list[Meeting]:
        """組織主催者の最近の会議を新しい順に返す (パーティション内クエリ)。

        partition_key=organizer_id なので cross-partition は不要。
        ランディング画面の「最近の会議」一覧で使用。
        """
        container = await self._get_container()
        query = (
            "SELECT * FROM c WHERE c.organizer_id = @oid "
            "ORDER BY c.started_at DESC OFFSET 0 LIMIT @lim"
        )
        params = [
            {"name": "@oid", "value": organizer_id},
            {"name": "@lim", "value": limit},
        ]
        items: list[Meeting] = []
        async for raw in container.query_items(
            query=query, parameters=params, partition_key=organizer_id
        ):
            items.append(Meeting.model_validate(raw))
        return items

    async def list_series(
        self, series_id: str, organizer_id: str
    ) -> list[Meeting]:
        """同シリーズの会議をシリーズ順 (series_index 昇順) で返す。

        partition_key=organizer_id を指定するとシングルパーティション query になる。
        異なる主催者が同じ series_id を共有するケースは現状想定しない。
        """
        container = await self._get_container()
        query = (
            "SELECT * FROM c WHERE c.series_id = @sid "
            "ORDER BY c.series_index ASC"
        )
        params = [{"name": "@sid", "value": series_id}]
        items: list[Meeting] = []
        async for raw in container.query_items(
            query=query, parameters=params, partition_key=organizer_id
        ):
            items.append(Meeting.model_validate(raw))
        return items
