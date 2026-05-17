"""Document endpoints — 会議に紐付く文書のアップロード / 一覧。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from helmsman.api.security import require_api_key
from helmsman.models.document import Document
from helmsman.repositories.documents import DocumentRepository
from helmsman.repositories.meetings import MeetingRepository
from helmsman.services.document_pipeline import ingest_document

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
        raise HTTPException(413, f"file too large (>{MAX_UPLOAD_BYTES // 1024 // 1024} MB)")
    if not data:
        raise HTTPException(400, "empty file")

    document = await ingest_document(
        meeting_id=meeting_id,
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
    """会議に紐付く文書一覧。"""
    meeting = await meeting_repo.get(meeting_id, organizer_id)
    if not meeting:
        raise HTTPException(404, "meeting not found")
    return await doc_repo.list_by_meeting(meeting_id)
