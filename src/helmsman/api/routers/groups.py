"""Group endpoints — 会議グループの CRUD + グループ文書 + 会議所属管理。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from helmsman.api.security import require_api_key
from helmsman.core.logging import logger
from helmsman.models.document import Document
from helmsman.models.group import MeetingGroup
from helmsman.models.meeting import Meeting
from helmsman.repositories.documents import GroupDocumentRepository
from helmsman.repositories.groups import GroupRepository
from helmsman.repositories.meetings import MeetingRepository
from helmsman.services.blob import delete_document_blob, generate_download_sas_url
from helmsman.services.document_pipeline import ingest_group_document

router = APIRouter(
    prefix="/groups",
    tags=["groups"],
    dependencies=[Depends(require_api_key)],
)

MAX_UPLOAD_BYTES = 25 * 1024 * 1024


def _group_repo() -> GroupRepository:
    return GroupRepository()


def _group_doc_repo() -> GroupDocumentRepository:
    return GroupDocumentRepository()


def _meeting_repo() -> MeetingRepository:
    return MeetingRepository()


# ---------- request / response ----------

class CreateGroupRequest(BaseModel):
    organizer_id: str
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=600)
    accent_hex: str | None = None


class UpdateGroupRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=600)
    accent_hex: str | None = None


class DownloadResponse(BaseModel):
    url: str
    expires_in_seconds: int


# ---------- group CRUD ----------

@router.post("", response_model=MeetingGroup, status_code=201)
async def create_group(
    req: CreateGroupRequest,
    repo: GroupRepository = Depends(_group_repo),
) -> MeetingGroup:
    group = MeetingGroup(
        organizer_id=req.organizer_id,
        name=req.name,
        description=req.description,
        accent_hex=req.accent_hex,
    )
    await repo.create(group)
    return group


@router.get("", response_model=list[MeetingGroup])
async def list_groups(
    organizer_id: str,
    limit: int = 50,
    repo: GroupRepository = Depends(_group_repo),
) -> list[MeetingGroup]:
    return await repo.list_by_organizer(organizer_id, limit=limit)


@router.get("/{group_id}", response_model=MeetingGroup)
async def get_group(
    group_id: str,
    organizer_id: str,
    repo: GroupRepository = Depends(_group_repo),
) -> MeetingGroup:
    group = await repo.get(group_id, organizer_id)
    if not group:
        raise HTTPException(404, "group not found")
    return group


@router.patch("/{group_id}", response_model=MeetingGroup)
async def update_group(
    group_id: str,
    organizer_id: str,
    req: UpdateGroupRequest,
    repo: GroupRepository = Depends(_group_repo),
) -> MeetingGroup:
    group = await repo.get(group_id, organizer_id)
    if not group:
        raise HTTPException(404, "group not found")
    if req.name is not None:
        group.name = req.name
    if req.description is not None:
        group.description = req.description
    if req.accent_hex is not None:
        group.accent_hex = req.accent_hex
    await repo.upsert(group)
    return group


@router.delete("/{group_id}", status_code=204)
async def delete_group(
    group_id: str,
    organizer_id: str,
    repo: GroupRepository = Depends(_group_repo),
    doc_repo: GroupDocumentRepository = Depends(_group_doc_repo),
    meeting_repo: MeetingRepository = Depends(_meeting_repo),
) -> None:
    """グループを削除。配下の文書も全て削除し、メンバー会議は group_id をクリア。"""
    group = await repo.get(group_id, organizer_id)
    if not group:
        raise HTTPException(404, "group not found")

    # 配下文書を全消し (Blob + Cosmos)
    docs = await doc_repo.list_by_group(group_id)
    for d in docs:
        try:
            await delete_document_blob(blob_path=d.blob_path)
        except Exception:  # noqa: BLE001
            pass
        await doc_repo.delete(d.id, group_id)

    # メンバー会議の group_id をクリア (孤児にしない)
    for meeting_id in group.meeting_ids:
        m = await meeting_repo.get(meeting_id, organizer_id)
        if m and m.group_id == group_id:
            m.group_id = None
            await meeting_repo.upsert(m)

    await repo.delete(group_id, organizer_id)


# ---------- group ↔ meeting attach ----------

@router.post("/{group_id}/meetings/{meeting_id}", response_model=Meeting)
async def attach_meeting(
    group_id: str,
    meeting_id: str,
    organizer_id: str,
    repo: GroupRepository = Depends(_group_repo),
    meeting_repo: MeetingRepository = Depends(_meeting_repo),
) -> Meeting:
    """会議をグループに追加 (既に group_id があれば置換)。"""
    group = await repo.get(group_id, organizer_id)
    if not group:
        raise HTTPException(404, "group not found")
    meeting = await meeting_repo.get(meeting_id, organizer_id)
    if not meeting:
        raise HTTPException(404, "meeting not found")

    # 以前のグループから外す
    if meeting.group_id and meeting.group_id != group_id:
        prev = await repo.get(meeting.group_id, organizer_id)
        if prev and meeting_id in prev.meeting_ids:
            prev.meeting_ids = [m for m in prev.meeting_ids if m != meeting_id]
            await repo.upsert(prev)

    meeting.group_id = group_id
    await meeting_repo.upsert(meeting)

    if meeting_id not in group.meeting_ids:
        group.meeting_ids.append(meeting_id)
        await repo.upsert(group)
    return meeting


@router.delete("/{group_id}/meetings/{meeting_id}", response_model=Meeting)
async def detach_meeting(
    group_id: str,
    meeting_id: str,
    organizer_id: str,
    repo: GroupRepository = Depends(_group_repo),
    meeting_repo: MeetingRepository = Depends(_meeting_repo),
) -> Meeting:
    """会議をグループから外す。"""
    group = await repo.get(group_id, organizer_id)
    if not group:
        raise HTTPException(404, "group not found")
    meeting = await meeting_repo.get(meeting_id, organizer_id)
    if not meeting:
        raise HTTPException(404, "meeting not found")
    if meeting.group_id == group_id:
        meeting.group_id = None
        await meeting_repo.upsert(meeting)
    if meeting_id in group.meeting_ids:
        group.meeting_ids = [m for m in group.meeting_ids if m != meeting_id]
        await repo.upsert(group)
    return meeting


@router.get("/{group_id}/meetings", response_model=list[Meeting])
async def list_group_meetings(
    group_id: str,
    organizer_id: str,
    repo: GroupRepository = Depends(_group_repo),
    meeting_repo: MeetingRepository = Depends(_meeting_repo),
) -> list[Meeting]:
    """グループに属する会議一覧 (新しい順)。"""
    group = await repo.get(group_id, organizer_id)
    if not group:
        raise HTTPException(404, "group not found")
    meetings: list[Meeting] = []
    for mid in group.meeting_ids:
        m = await meeting_repo.get(mid, organizer_id)
        if m:
            meetings.append(m)
    meetings.sort(key=lambda m: m.started_at or m.id, reverse=True)
    return meetings


# ---------- group documents ----------

@router.post("/{group_id}/documents", response_model=Document, status_code=201)
async def upload_group_document(
    group_id: str,
    organizer_id: str,
    file: UploadFile = File(...),
    uploaded_by: str = Form(...),
    repo: GroupRepository = Depends(_group_repo),
    doc_repo: GroupDocumentRepository = Depends(_group_doc_repo),
) -> Document:
    group = await repo.get(group_id, organizer_id)
    if not group:
        raise HTTPException(404, "group not found")

    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            413, f"file too large (>{MAX_UPLOAD_BYTES // 1024 // 1024} MB)"
        )
    if not data:
        raise HTTPException(400, "empty file")

    document = await ingest_group_document(
        group_id=group_id,
        organizer_id=organizer_id,
        uploaded_by=uploaded_by,
        filename=file.filename or "untitled",
        mime_type=file.content_type or "application/octet-stream",
        data=data,
        repo=doc_repo,
    )

    if document.id not in group.document_ids:
        group.document_ids.append(document.id)
        await repo.upsert(group)

    logger.info(
        "group.document_uploaded",
        group_id=group_id,
        document_id=document.id,
        status=document.status,
    )
    return document


@router.get("/{group_id}/documents", response_model=list[Document])
async def list_group_documents(
    group_id: str,
    organizer_id: str,
    repo: GroupRepository = Depends(_group_repo),
    doc_repo: GroupDocumentRepository = Depends(_group_doc_repo),
) -> list[Document]:
    group = await repo.get(group_id, organizer_id)
    if not group:
        raise HTTPException(404, "group not found")
    return await doc_repo.list_by_group(group_id)


@router.delete("/{group_id}/documents/{document_id}", status_code=204)
async def delete_group_document(
    group_id: str,
    document_id: str,
    organizer_id: str,
    repo: GroupRepository = Depends(_group_repo),
    doc_repo: GroupDocumentRepository = Depends(_group_doc_repo),
) -> None:
    group = await repo.get(group_id, organizer_id)
    if not group:
        raise HTTPException(404, "group not found")
    document = await doc_repo.get(document_id, group_id)
    if not document:
        raise HTTPException(404, "document not found")

    try:
        await delete_document_blob(blob_path=document.blob_path)
    except Exception:  # noqa: BLE001
        pass
    await doc_repo.delete(document_id, group_id)

    if document_id in group.document_ids:
        group.document_ids = [d for d in group.document_ids if d != document_id]
        await repo.upsert(group)


@router.get(
    "/{group_id}/documents/{document_id}/download", response_model=DownloadResponse
)
async def download_group_document(
    group_id: str,
    document_id: str,
    organizer_id: str,
    repo: GroupRepository = Depends(_group_repo),
    doc_repo: GroupDocumentRepository = Depends(_group_doc_repo),
) -> DownloadResponse:
    group = await repo.get(group_id, organizer_id)
    if not group:
        raise HTTPException(404, "group not found")
    document = await doc_repo.get(document_id, group_id)
    if not document:
        raise HTTPException(404, "document not found")

    url = generate_download_sas_url(blob_path=document.blob_path)
    if not url:
        raise HTTPException(503, "blob storage not configured")
    return DownloadResponse(url=url, expires_in_seconds=15 * 60)
