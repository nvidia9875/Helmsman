"""FaceSignalBatch を Cosmos に永続化する repository (Phase 6)。

partition `/meeting_id`、TTL 30 日 (Cosmos 側で設定推奨)。
事後分析・レポート生成用。EngagementAgent はこっちではなく in-memory buffer を読む。
"""
from __future__ import annotations

from azure.cosmos.aio import ContainerProxy

from helmsman.models.face_signal import FaceSignalBatch
from helmsman.repositories.cosmos import get_database


class FaceSignalRepository:
    CONTAINER = "face_signals"

    def __init__(self) -> None:
        self._container: ContainerProxy | None = None

    async def _get_container(self) -> ContainerProxy:
        if self._container is None:
            self._container = get_database().get_container_client(self.CONTAINER)
        return self._container

    async def create(self, batch: FaceSignalBatch) -> FaceSignalBatch:
        container = await self._get_container()
        await container.create_item(body=batch.model_dump(mode="json"))
        return batch

    async def list_by_meeting(
        self, meeting_id: str, limit: int = 200
    ) -> list[FaceSignalBatch]:
        """会議の face signal batch 一覧 (古い順、レポート時系列分析用)。"""
        container = await self._get_container()
        query = (
            "SELECT * FROM c WHERE c.meeting_id = @mid "
            "ORDER BY c.received_at ASC OFFSET 0 LIMIT @lim"
        )
        params = [
            {"name": "@mid", "value": meeting_id},
            {"name": "@lim", "value": limit},
        ]
        items: list[FaceSignalBatch] = []
        async for raw in container.query_items(
            query=query, parameters=params, partition_key=meeting_id
        ):
            items.append(FaceSignalBatch.model_validate(raw))
        return items
