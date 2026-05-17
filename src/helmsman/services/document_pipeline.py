"""文書アップロード → 抽出 → 索引化のオーケストレーション。

呼び出し側 (API router) はこの 2 関数だけ知っていればよい:
  - ingest_meeting_document : 会議スコープ
  - ingest_group_document   : グループスコープ
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from helmsman.core.logging import logger
from helmsman.core.pricing import calculate_cost_usd
from helmsman.core.usage import MeetingUsage
from helmsman.models.document import (
    Document,
    DocumentChunk,
    DocumentScope,
    DocumentStatus,
)
from helmsman.repositories.documents import (
    DocumentRepository,
    GroupDocumentRepository,
)
from helmsman.services.blob import upload_document_blob
from helmsman.services.chunking import chunk_text
from helmsman.services.document_extractor import extract_text
from helmsman.services.embeddings import embed_texts
from helmsman.services.search_index import ensure_index, upsert_chunks


async def _process_document(
    document: Document,
    data: bytes,
    save: Callable[[Document], Awaitable[Document]],
    usage_sink: MeetingUsage | None,
) -> Document:
    """共通パイプライン: Blob → extract → chunk → embed → search index。

    各 step で失敗してもユーザに 500 を返さず、status=FAILED で記録する。
    """
    try:
        await upload_document_blob(
            owner_id=document.owner_id,
            document_id=document.id,
            filename=document.filename,
            data=data,
            content_type=document.mime_type,
        )

        document.status = DocumentStatus.EXTRACTING
        await save(document)

        text = await extract_text(data, document.mime_type, document.filename)
        document.extracted_text = text
        document.extracted_at = datetime.now(UTC)

        chunks_text = chunk_text(text)
        document.chunk_count = len(chunks_text)
        chunks = [
            DocumentChunk(
                document_id=document.id,
                meeting_id=document.meeting_id,
                group_id=document.group_id,
                chunk_index=i,
                text=t,
            )
            for i, t in enumerate(chunks_text)
        ]

        if chunks:
            try:
                vectors, usage = await embed_texts([c.text for c in chunks])
                for chunk, vec in zip(chunks, vectors, strict=False):
                    chunk.embedding = vec
                if usage and usage_sink is not None:
                    usage_sink.apply(usage, calculate_cost_usd(usage))

                await ensure_index()
                upserted = await upsert_chunks(chunks)
                if upserted > 0:
                    document.index_provider = "azure_ai_search"
                    document.search_index_name = "helmsman-documents"
            except Exception as e:  # noqa: BLE001
                logger.warning(
                    "document.indexing_failed",
                    document_id=document.id,
                    error=str(e),
                )

        document.status = DocumentStatus.INDEXED
        await save(document)
        return document

    except Exception as e:  # noqa: BLE001
        logger.error(
            "document.ingest_failed",
            document_id=document.id,
            error=str(e),
            error_type=type(e).__name__,
        )
        document.status = DocumentStatus.FAILED
        document.error_message = str(e)[:500]
        await save(document)
        return document


async def ingest_meeting_document(
    *,
    meeting_id: str,
    organizer_id: str,
    uploaded_by: str,
    filename: str,
    mime_type: str,
    data: bytes,
    repo: DocumentRepository,
    usage_sink: MeetingUsage | None = None,
) -> Document:
    """1 文書を fully process し、会議スコープで保存。"""
    document = Document(
        scope=DocumentScope.MEETING,
        meeting_id=meeting_id,
        organizer_id=organizer_id,
        filename=filename,
        mime_type=mime_type,
        size_bytes=len(data),
        blob_path=f"{meeting_id}/__placeholder__/{filename}",
        uploaded_by=uploaded_by,
    )
    document.blob_path = f"{meeting_id}/{document.id}/{filename}"
    await repo.create(document)
    return await _process_document(document, data, repo.upsert, usage_sink)


async def ingest_group_document(
    *,
    group_id: str,
    organizer_id: str,
    uploaded_by: str,
    filename: str,
    mime_type: str,
    data: bytes,
    repo: GroupDocumentRepository,
    usage_sink: MeetingUsage | None = None,
) -> Document:
    """1 文書を fully process し、グループスコープで保存。"""
    document = Document(
        scope=DocumentScope.GROUP,
        group_id=group_id,
        organizer_id=organizer_id,
        filename=filename,
        mime_type=mime_type,
        size_bytes=len(data),
        blob_path=f"{group_id}/__placeholder__/{filename}",
        uploaded_by=uploaded_by,
    )
    document.blob_path = f"{group_id}/{document.id}/{filename}"
    await repo.create(document)
    return await _process_document(document, data, repo.upsert, usage_sink)


# 後方互換 alias
ingest_document = ingest_meeting_document
