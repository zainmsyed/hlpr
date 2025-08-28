"""Meeting endpoints for Phase 1."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from hlpr.db.dependencies import get_session
from hlpr.db.repositories import DocumentRepository, MeetingRepository, PipelineRunRepository
from hlpr.services.pipelines import PipelineService

router = APIRouter(prefix="/meetings", tags=["meetings"])


class MeetingCreate(BaseModel):
    project_id: int
    title: str
    transcript: str
    participants: list[str] | None = None


class MeetingOut(BaseModel):
    id: int
    project_id: int
    title: str
    transcript: str
    participants: list[str] | None = None

    @classmethod
    def from_orm_obj(cls, meeting: Any) -> MeetingOut:
        participants = meeting.participants.split(",") if meeting.participants else None
        return cls(
            id=meeting.id,
            project_id=meeting.project_id,
            title=meeting.title,
            transcript=meeting.transcript,
            participants=participants,
        )


@router.post("/")
async def create_meeting(
    meeting: MeetingCreate, session: AsyncSession = Depends(get_session)  # noqa: B008
) -> dict[str, Any]:
    repo = MeetingRepository(session)
    meeting_record = await repo.add(
        project_id=meeting.project_id,
        title=meeting.title,
        transcript=meeting.transcript,
        participants=meeting.participants,
    )
    await session.commit()
    return {
        "id": meeting_record.id,
        "title": meeting_record.title,
        "participants": meeting_record.participants,
        "transcript": meeting_record.transcript,
        "created_at": meeting_record.created_at.isoformat() if meeting_record.created_at else None,
    }


@router.get("/{meeting_id}", response_model=MeetingOut)
async def get_meeting(
    meeting_id: int, session: AsyncSession = Depends(get_session)  # noqa: B008
) -> MeetingOut:
    repo = MeetingRepository(session)
    meeting = await repo.get(meeting_id)
    if meeting is None:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return MeetingOut.from_orm_obj(meeting)


@router.post("/{meeting_id}/summarize")
async def summarize_meeting(
    meeting_id: int, session: AsyncSession = Depends(get_session)  # noqa: B008
) -> dict[str, Any]:
    meeting_repo = MeetingRepository(session)
    docs_repo = DocumentRepository(session)
    runs_repo = PipelineRunRepository(session)
    service = PipelineService(docs_repo, runs_repo)
    try:
        output: dict[str, Any] = await service._run_meeting_summarization(meeting_repo, meeting_id)
    except ValueError as err:  # B904: explicit chaining
        raise HTTPException(status_code=404, detail="Meeting not found") from err
    await session.commit()
    return output
