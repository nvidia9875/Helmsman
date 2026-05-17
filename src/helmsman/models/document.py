"""Document — 会議 or グループに紐付くアップロード資料。"""
from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator


class DocumentStatus(str, Enum):
    UPLOADED = "uploaded"
    EXTRACTING = "extracting"
    INDEXED = "indexed"
    FAILED = "failed"


class DocumentScope(str, Enum):
    """文書のオーナー種別。

    MEETING: 単一会議に紐付く (meeting_id をパーティション)
    GROUP:   グループに紐付き、配下の全会議の RAG に流れる (group_id をパーティション)
    """

    MEETING = "meeting"
    GROUP = "group"


class Document(BaseModel):
    """参照文書 (PDF/Word/PPT/MD)。Blob に実体、Cosmos にメタ。

    `scope` が MEETING なら meeting_id が必須、GROUP なら group_id が必須。
    どちらか片方だけ set。
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    scope: DocumentScope = DocumentScope.MEETING
    meeting_id: str | None = None
    group_id: str | None = None
    organizer_id: str | None = None  # 所有者 — グループ文書の認可で使う

    filename: str
    mime_type: str
    size_bytes: int

    blob_container: str = "documents"
    blob_path: str  # `<owner_id>/<id>/<filename>` 形式

    extracted_text: str | None = None  # Document Intelligence で抽出された全文
    extracted_at: datetime | None = None
    chunk_count: int = 0  # ベクトル化後の chunk 数

    index_provider: str | None = None  # "azure_ai_search" / "cosmos_vector"
    search_index_name: str | None = None

    status: DocumentStatus = DocumentStatus.UPLOADED
    error_message: str | None = None

    uploaded_by: str
    uploaded_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @model_validator(mode="after")
    def _exactly_one_owner(self) -> Document:
        if self.scope == DocumentScope.MEETING and not self.meeting_id:
            raise ValueError("meeting_id required when scope=meeting")
        if self.scope == DocumentScope.GROUP and not self.group_id:
            raise ValueError("group_id required when scope=group")
        return self

    @property
    def owner_id(self) -> str:
        """検索インデックスや RAG が使うオーナー識別子 (meeting_id or group_id)。"""
        if self.scope == DocumentScope.GROUP:
            return self.group_id or ""
        return self.meeting_id or ""


class DocumentChunk(BaseModel):
    """ベクトル化のために分割されたチャンク。Cosmos Vector / AI Search に格納。"""

    id: str = Field(default_factory=lambda: str(uuid4()))
    document_id: str
    meeting_id: str | None = None
    group_id: str | None = None
    chunk_index: int
    text: str
    embedding: list[float] | None = None  # 後で埋める
    source_page: int | None = None
    source_section: str | None = None

    @property
    def owner_id(self) -> str:
        """検索 filter で使うオーナー識別子。"""
        return self.group_id or self.meeting_id or ""
