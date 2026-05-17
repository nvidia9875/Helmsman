"""Cosmos DB client (async, serverless)."""
from __future__ import annotations

from functools import lru_cache

from azure.cosmos.aio import CosmosClient, DatabaseProxy

from helmsman.core.config import get_settings


@lru_cache(maxsize=1)
def _client() -> CosmosClient:
    settings = get_settings()
    return CosmosClient(
        url=settings.cosmos_endpoint,
        credential=settings.cosmos_key,
    )


def get_cosmos_client() -> CosmosClient:
    """Async Cosmos client singleton."""
    return _client()


def get_database() -> DatabaseProxy:
    settings = get_settings()
    return get_cosmos_client().get_database_client(settings.cosmos_database)
