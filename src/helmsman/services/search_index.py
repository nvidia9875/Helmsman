"""Azure AI Search 索引操作 + ベクトル検索 (文書 RAG 用)。

Index schema (chunk 単位で 1 doc):
  id: str (key)
  document_id: str (filterable)
  meeting_id: str (filterable)
  chunk_index: int
  text: str (searchable)
  embedding: Collection(Edm.Single), HNSW vector field
"""
from __future__ import annotations

from helmsman.core.config import get_settings
from helmsman.core.logging import logger
from helmsman.models.document import DocumentChunk

VECTOR_DIM = 1536  # text-embedding-3-small
VECTOR_FIELD = "embedding"


def _is_configured() -> bool:
    s = get_settings()
    return bool(s.azure_search_endpoint and s.azure_search_key)


async def ensure_index() -> None:
    """インデックスが存在しなければ作る (idempotent)。"""
    if not _is_configured():
        return
    s = get_settings()
    from azure.core.credentials import AzureKeyCredential
    from azure.search.documents.indexes.aio import SearchIndexClient
    from azure.search.documents.indexes.models import (
        HnswAlgorithmConfiguration,
        SearchableField,
        SearchField,
        SearchFieldDataType,
        SearchIndex,
        SimpleField,
        VectorSearch,
        VectorSearchProfile,
    )

    fields = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True),
        SimpleField(
            name="document_id", type=SearchFieldDataType.String, filterable=True
        ),
        SimpleField(
            name="meeting_id", type=SearchFieldDataType.String, filterable=True
        ),
        SimpleField(
            name="group_id", type=SearchFieldDataType.String, filterable=True
        ),
        SimpleField(name="chunk_index", type=SearchFieldDataType.Int32),
        SearchableField(name="text", type=SearchFieldDataType.String),
        SearchField(
            name=VECTOR_FIELD,
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=VECTOR_DIM,
            vector_search_profile_name="hnsw-profile",
        ),
    ]
    vector_search = VectorSearch(
        algorithms=[HnswAlgorithmConfiguration(name="hnsw-config")],
        profiles=[
            VectorSearchProfile(
                name="hnsw-profile",
                algorithm_configuration_name="hnsw-config",
            )
        ],
    )
    index = SearchIndex(
        name=s.azure_search_index_name,
        fields=fields,
        vector_search=vector_search,
    )
    async with SearchIndexClient(
        endpoint=s.azure_search_endpoint or "",
        credential=AzureKeyCredential(s.azure_search_key or ""),
    ) as client:
        await client.create_or_update_index(index)
    logger.info("search.index_ensured", name=s.azure_search_index_name)


async def upsert_chunks(chunks: list[DocumentChunk]) -> int:
    """ベクトル付きチャンクを索引にアップサート。返り値は upsert 件数。"""
    if not _is_configured() or not chunks:
        return 0
    s = get_settings()
    from azure.core.credentials import AzureKeyCredential
    from azure.search.documents.aio import SearchClient

    docs = [
        {
            "id": c.id,
            "document_id": c.document_id,
            "meeting_id": c.meeting_id or "",
            "group_id": c.group_id or "",
            "chunk_index": c.chunk_index,
            "text": c.text,
            VECTOR_FIELD: c.embedding or [],
        }
        for c in chunks
        if c.embedding
    ]
    async with SearchClient(
        endpoint=s.azure_search_endpoint or "",
        index_name=s.azure_search_index_name,
        credential=AzureKeyCredential(s.azure_search_key or ""),
    ) as client:
        result = await client.upload_documents(documents=docs)
    succeeded = sum(1 for r in result if r.succeeded)
    logger.info("search.upserted", count=succeeded, attempted=len(docs))
    return succeeded


async def search_meeting_chunks(
    *,
    meeting_id: str,
    group_id: str | None = None,
    query_embedding: list[float],
    top_k: int = 5,
) -> list[dict]:
    """会議 (および任意で所属グループ) に絞ってベクトル検索。

    group_id が渡された場合、`meeting_id eq X or group_id eq Y` で OR 検索する。
    返り値は raw chunk dict のリスト。
    """
    if not _is_configured() or not query_embedding:
        return []
    s = get_settings()
    from azure.core.credentials import AzureKeyCredential
    from azure.search.documents.aio import SearchClient
    from azure.search.documents.models import VectorizedQuery

    vector_query = VectorizedQuery(
        vector=query_embedding,
        k_nearest_neighbors=top_k,
        fields=VECTOR_FIELD,
    )
    if group_id:
        filter_expr = (
            f"meeting_id eq '{meeting_id}' or group_id eq '{group_id}'"
        )
    else:
        filter_expr = f"meeting_id eq '{meeting_id}'"

    results: list[dict] = []
    async with SearchClient(
        endpoint=s.azure_search_endpoint or "",
        index_name=s.azure_search_index_name,
        credential=AzureKeyCredential(s.azure_search_key or ""),
    ) as client:
        response = await client.search(
            search_text=None,
            vector_queries=[vector_query],
            filter=filter_expr,
            top=top_k,
        )
        async for raw in response:
            results.append(dict(raw))
    return results
