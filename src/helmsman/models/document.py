"""Document — 会議に紐付くアップロード資料。"""
from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field


class DocumentStatus(str, Enum):
    UPLOADED = "uploaded"
    EXTRACTING = "extracting"
    INDEXED = "indexed"
    FAILED = "failed"


class Document(BaseModel):
    """会議の参照文書 (PDF/Word/PPT/MD)。Blob に実体、Cosmos にメタ。"""

    id: str = Field(default_factory=lambda: str(uuid4()))
    meeting_id: str
    filename: str
    mime_type: str
    size_bytes: int

    blob_container: str = "documents"
    blob_path: str  # `<meeting_id>/<id>/<filename>` 形式

    extracted_text: str | None = None  # Document Intelligence で抽出された全文
    extracted_at: datetime | None = None
    chunk_count: int = 0  # ベクトル化後の chunk 数

    index_provider: str | None = None  # "azure_ai_search" / "cosmos_vector"
    search_index_name: str | None = None

    status: DocumentStatus = DocumentStatus.UPLOADED
    error_message: str | None = None

    uploaded_by: str
    uploaded_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class DocumentChunk(BaseModel):
    """ベクトル化のために分割されたチャンク。Cosmos Vector / AI Search に格納。"""

    id: str = Field(default_factory=lambda: str(uuid4()))
    document_id: str
    meeting_id: str
    chunk_index: int
    text: str
    embedding: list[float] | None = None  # 後で埋める
    source_page: int | None = None
    source_section: str | None = None
