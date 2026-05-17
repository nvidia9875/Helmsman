"""Document endpoints — 会議に紐付く文書のアップロード / 一覧 / 削除 / ダウンロード。

グループ文書は routers/groups.py 側で扱う。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from helmsman.api.security import require_api_key
from helmsman.models.document import Document
from helmsman.repositories.documents import DocumentRepository
from helmsman.repositories.meetings import MeetingRepository
from helmsman.services.blob import delete_document_blob, generate_download_sas_url
from helmsman.services.document_pipeline import ingest_meeting_document

router = APIRouter(
    prefix="/meetings/{meeting_id}/documents",
    tags=["documents"],
    dependencies=[Depends(require_api_key)],
)

MAX_UPLOAD_BYTES = 25 * 1024 * 1024  # 25MB


def get_doc_repo() -> DocumentRepository:
    return DocumentRepository()


def get_meeting_repo() -> MeetingRepository:
    return MeetingRepository()


class DownloadResponse(BaseModel):
    url: str
    expires_in_seconds: int


@router.post("", response_model=Document, status_code=201)
async def upload_document(
    meeting_id: str,
    organizer_id: str,
    file: UploadFile = File(...),
    uploaded_by: str = Form(...),
    doc_repo: DocumentRepository = Depends(get_doc_repo),
    meeting_repo: MeetingRepository = Depends(get_meeting_repo),
) -> Document:
    """1 ファイルをアップロード → 抽出 → 索引化。

    成功時は INDEXED な Document を返す。
    抽出/索引化失敗時は status=FAILED の Document を返す (HTTP 201 のまま、UI 側で確認)。
    """
    meeting = await meeting_repo.get(meeting_id, organizer_id)
    if not meeting:
        raise HTTPException(404, "meeting not found")

    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            413, f"file too large (>{MAX_UPLOAD_BYTES // 1024 // 1024} MB)"
        )
    if not data:
        raise HTTPException(400, "empty file")

    document = await ingest_meeting_document(
        meeting_id=meeting_id,
        organizer_id=organizer_id,
        uploaded_by=uploaded_by,
        filename=file.filename or "untitled",
        mime_type=file.content_type or "application/octet-stream",
        data=data,
        repo=doc_repo,
        usage_sink=meeting.usage,
    )

    # 会議メタに紐付け
    if document.id not in meeting.document_ids:
        meeting.document_ids.append(document.id)
    if document.search_index_name and not meeting.document_index_name:
        meeting.document_index_name = document.search_index_name
    await meeting_repo.upsert(meeting)

    return document


@router.get("", response_model=list[Document])
async def list_documents(
    meeting_id: str,
    organizer_id: str,
    doc_repo: DocumentRepository = Depends(get_doc_repo),
    meeting_repo: MeetingRepository = Depends(get_meeting_repo),
) -> list[Document]:
    """会議に紐付く文書一覧 (会議スコープのみ。group 文書は含まない)。"""
    meeting = await meeting_repo.get(meeting_id, organizer_id)
    if not meeting:
        raise HTTPException(404, "meeting not found")
    return await doc_repo.list_by_meeting(meeting_id)


@router.delete("/{document_id}", status_code=204)
async def delete_document(
    meeting_id: str,
    document_id: str,
    organizer_id: str,
    doc_repo: DocumentRepository = Depends(get_doc_repo),
    meeting_repo: MeetingRepository = Depends(get_meeting_repo),
) -> None:
    """文書を 1 件削除 (Cosmos メタ + Blob 実体)。"""
    meeting = await meeting_repo.get(meeting_id, organizer_id)
    if not meeting:
        raise HTTPException(404, "meeting not found")

    document = await doc_repo.get(document_id, meeting_id)
    if not document:
        raise HTTPException(404, "document not found")

    # Blob を消す (失敗してもメタは消す — 孤児 blob を残すよりは UI 整合性優先)
    try:
        await delete_document_blob(blob_path=document.blob_path)
    except Exception:  # noqa: BLE001
        pass
    await doc_repo.delete(document_id, meeting_id)

    if document_id in meeting.document_ids:
        meeting.document_ids = [d for d in meeting.document_ids if d != document_id]
        await meeting_repo.upsert(meeting)


@router.get("/{document_id}/download", response_model=DownloadResponse)
async def download_document(
    meeting_id: str,
    document_id: str,
    organizer_id: str,
    doc_repo: DocumentRepository = Depends(get_doc_repo),
    meeting_repo: MeetingRepository = Depends(get_meeting_repo),
) -> DownloadResponse:
    """短命の read-only SAS URL を発行 (プレビュー / ダウンロード用)。"""
    meeting = await meeting_repo.get(meeting_id, organizer_id)
    if not meeting:
        raise HTTPException(404, "meeting not found")

    document = await doc_repo.get(document_id, meeting_id)
    if not document:
        raise HTTPException(404, "document not found")

    url = generate_download_sas_url(blob_path=document.blob_path)
    if not url:
        raise HTTPException(503, "blob storage not configured")

    return DownloadResponse(url=url, expires_in_seconds=15 * 60)
