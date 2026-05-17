"""文書アップロード → 抽出 → 索引化のオーケストレーション。

呼び出し側 (API router) はこの 1 関数だけ知っていればよい。
"""
from __future__ import annotations

from datetime import UTC, datetime

from helmsman.core.logging import logger
from helmsman.core.pricing import calculate_cost_usd
from helmsman.core.usage import MeetingUsage
from helmsman.models.document import Document, DocumentChunk, DocumentStatus
from helmsman.repositories.documents import DocumentRepository
from helmsman.services.blob import upload_document_blob
from helmsman.services.chunking import chunk_text
from helmsman.services.document_extractor import extract_text
from helmsman.services.embeddings import embed_texts
from helmsman.services.search_index import (
    ensure_index,
    upsert_chunks,
)


async def ingest_document(
    *,
    meeting_id: str,
    uploaded_by: str,
    filename: str,
    mime_type: str,
    data: bytes,
    repo: DocumentRepository,
    usage_sink: MeetingUsage | None = None,
) -> Document:
    """1 文書を fully process し、Document を返す。

    Steps:
      1. Document メタを Cosmos に create (status=UPLOADED)
      2. Blob にアップロード (連携あれば)
      3. テキスト抽出 (DocIntel or pypdf)
      4. チャンク分割
      5. 埋め込み生成
      6. AI Search に upsert
      7. status を INDEXED に更新

    各 step で失敗してもユーザに 500 を返さず、status=FAILED で記録する。
    """
    document = Document(
        meeting_id=meeting_id,
        filename=filename,
        mime_type=mime_type,
        size_bytes=len(data),
        blob_path="",  # 後で埋める
        uploaded_by=uploaded_by,
    )
    document.blob_path = f"{meeting_id}/{document.id}/{filename}"
    await repo.create(document)

    try:
        # Step 2: Blob upload
        await upload_document_blob(
            meeting_id=meeting_id,
            document_id=document.id,
            filename=filename,
            data=data,
            content_type=mime_type,
        )

        # Step 3: Extract text
        document.status = DocumentStatus.EXTRACTING
        await repo.upsert(document)
        text = await extract_text(data, mime_type, filename)
        document.extracted_text = text
        document.extracted_at = datetime.now(UTC)

        # Step 4: Chunk
        chunks_text = chunk_text(text)
        document.chunk_count = len(chunks_text)
        chunks = [
            DocumentChunk(
                document_id=document.id,
                meeting_id=meeting_id,
                chunk_index=i,
                text=t,
            )
            for i, t in enumerate(chunks_text)
        ]

        # Step 5+6: Embed + index (only if all 3 services configured)
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
                # 索引化失敗は致命的ではない (extracted_text だけで RAG 可)
                logger.warning(
                    "document.indexing_failed",
                    document_id=document.id,
                    error=str(e),
                )

        document.status = DocumentStatus.INDEXED
        await repo.upsert(document)
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
        await repo.upsert(document)
        return document
