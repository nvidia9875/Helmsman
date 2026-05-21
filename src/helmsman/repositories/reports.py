"""MeetingReport repository — Cosmos `meeting_reports` container."""
from __future__ import annotations

from azure.cosmos.aio import ContainerProxy
from azure.cosmos.exceptions import CosmosResourceNotFoundError

from helmsman.models.report import MeetingReport
from helmsman.repositories.cosmos import get_database


class MeetingReportRepository:
    CONTAINER = "meeting_reports"

    def __init__(self) -> None:
        self._container: ContainerProxy | None = None

    async def _get_container(self) -> ContainerProxy:
        if self._container is None:
            self._container = get_database().get_container_client(self.CONTAINER)
        return self._container

    async def create(self, report: MeetingReport) -> MeetingReport:
        container = await self._get_container()
        await container.create_item(body=report.model_dump(mode="json"))
        return report

    async def get(self, report_id: str, meeting_id: str) -> MeetingReport | None:
        container = await self._get_container()
        try:
            item = await container.read_item(item=report_id, partition_key=meeting_id)
            return MeetingReport.model_validate(item)
        except CosmosResourceNotFoundError:
            return None

    async def list_by_meeting(
        self, meeting_id: str, limit: int = 20
    ) -> list[MeetingReport]:
        """会議に紐付くレポート履歴を新しい順に返す。"""
        container = await self._get_container()
        query = (
            "SELECT * FROM c WHERE c.meeting_id = @mid "
            "ORDER BY c.generated_at DESC OFFSET 0 LIMIT @lim"
        )
        params = [
            {"name": "@mid", "value": meeting_id},
            {"name": "@lim", "value": limit},
        ]
        items: list[MeetingReport] = []
        async for raw in container.query_items(
            query=query, parameters=params, partition_key=meeting_id
        ):
            items.append(MeetingReport.model_validate(raw))
        return items

    async def latest(self, meeting_id: str) -> MeetingReport | None:
        """最新 1 件を返す。無ければ None。"""
        items = await self.list_by_meeting(meeting_id, limit=1)
        return items[0] if items else None
