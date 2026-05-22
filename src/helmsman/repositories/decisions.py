"""Decision repository — Cosmos `decisions` container (partition /organizer_id)。

Phase 7 (会議横断記憶) の永続化層。
DecisionCapture が高 confidence を出した瞬間に write-through で upsert される。
MemoryRetriever は ``list_by_organizer`` で organizer の全 decision を取得し、
AI Search 未デプロイ環境では numpy in-process cosine で類似度計算する (ADR-104)。
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from azure.cosmos.aio import ContainerProxy
from azure.cosmos.exceptions import CosmosResourceNotFoundError

from helmsman.models.decision import Decision
from helmsman.repositories.cosmos import get_database


class DecisionRepository:
    CONTAINER = "decisions"

    def __init__(self) -> None:
        self._container: ContainerProxy | None = None

    async def _get_container(self) -> ContainerProxy:
        if self._container is None:
            self._container = get_database().get_container_client(self.CONTAINER)
        return self._container

    async def upsert(self, decision: Decision) -> Decision:
        """deterministic id (`meeting_id:topic_id`) で重複なく upsert。"""
        decision.touch()
        container = await self._get_container()
        await container.upsert_item(body=decision.model_dump(mode="json"))
        return decision

    async def get(self, decision_id: str, organizer_id: str) -> Decision | None:
        container = await self._get_container()
        try:
            item = await container.read_item(
                item=decision_id, partition_key=organizer_id
            )
            return Decision.model_validate(item)
        except CosmosResourceNotFoundError:
            return None

    async def delete(self, decision_id: str, organizer_id: str) -> bool:
        container = await self._get_container()
        try:
            await container.delete_item(
                item=decision_id, partition_key=organizer_id
            )
            return True
        except CosmosResourceNotFoundError:
            return False

    async def list_by_organizer(
        self,
        organizer_id: str,
        *,
        within_days: int | None = 90,
        limit: int = 500,
    ) -> list[Decision]:
        """主催者の最近の decision 一覧 (新しい順)。

        partition_key=organizer_id でシングルパーティション query。
        ``within_days`` 指定時は ``captured_at`` でフィルタ (デフォルト 90 日)。
        MemoryRetriever のフォールバック path (numpy cosine) はこの一覧を全件 scan する。
        """
        container = await self._get_container()
        params: list[dict] = [{"name": "@oid", "value": organizer_id}]
        where = ["c.organizer_id = @oid"]
        if within_days is not None:
            cutoff = (datetime.now(UTC) - timedelta(days=within_days)).isoformat()
            where.append("c.captured_at >= @cutoff")
            params.append({"name": "@cutoff", "value": cutoff})
        params.append({"name": "@lim", "value": limit})
        query = (
            f"SELECT * FROM c WHERE {' AND '.join(where)} "
            "ORDER BY c.captured_at DESC OFFSET 0 LIMIT @lim"
        )
        items: list[Decision] = []
        async for raw in container.query_items(
            query=query, parameters=params, partition_key=organizer_id
        ):
            items.append(Decision.model_validate(raw))
        return items

    async def list_by_series(
        self, series_id: str, organizer_id: str, limit: int = 200
    ) -> list[Decision]:
        """同シリーズの decision を新しい順に。

        partition は organizer_id 1 つで済む (異 organizer 同 series は想定しない)。
        """
        container = await self._get_container()
        query = (
            "SELECT * FROM c "
            "WHERE c.organizer_id = @oid AND c.series_id = @sid "
            "ORDER BY c.captured_at DESC OFFSET 0 LIMIT @lim"
        )
        params = [
            {"name": "@oid", "value": organizer_id},
            {"name": "@sid", "value": series_id},
            {"name": "@lim", "value": limit},
        ]
        items: list[Decision] = []
        async for raw in container.query_items(
            query=query, parameters=params, partition_key=organizer_id
        ):
            items.append(Decision.model_validate(raw))
        return items

    async def list_by_group(
        self, group_id: str, organizer_id: str, limit: int = 200
    ) -> list[Decision]:
        """同グループの decision を新しい順に。"""
        container = await self._get_container()
        query = (
            "SELECT * FROM c "
            "WHERE c.organizer_id = @oid AND c.group_id = @gid "
            "ORDER BY c.captured_at DESC OFFSET 0 LIMIT @lim"
        )
        params = [
            {"name": "@oid", "value": organizer_id},
            {"name": "@gid", "value": group_id},
            {"name": "@lim", "value": limit},
        ]
        items: list[Decision] = []
        async for raw in container.query_items(
            query=query, parameters=params, partition_key=organizer_id
        ):
            items.append(Decision.model_validate(raw))
        return items

    async def list_by_meeting(
        self, meeting_id: str, organizer_id: str
    ) -> list[Decision]:
        """特定会議の decision (cross-partition だが organizer 1 つに絞れる)。"""
        container = await self._get_container()
        query = (
            "SELECT * FROM c "
            "WHERE c.organizer_id = @oid AND c.meeting_id = @mid "
            "ORDER BY c.captured_at ASC"
        )
        params = [
            {"name": "@oid", "value": organizer_id},
            {"name": "@mid", "value": meeting_id},
        ]
        items: list[Decision] = []
        async for raw in container.query_items(
            query=query, parameters=params, partition_key=organizer_id
        ):
            items.append(Decision.model_validate(raw))
        return items
