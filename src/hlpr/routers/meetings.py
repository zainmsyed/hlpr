"""Meeting endpoints for Phase 1."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from hlpr.db.dependencies import get_session
from hlpr.db.repositories import MeetingRepository, PipelineRunRepository
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
    def from_orm_obj(cls, meeting: Any) -> MeetingOut:  # type: ignore[name-defined]
        participants = meeting.participants.split(",") if meeting.participants else None
        return cls(
            id=meeting.id,
            project_id=meeting.project_id,
            title=meeting.title,
            transcript=meeting.transcript,
            participants=participants,
        )


@router.post("", response_model=MeetingOut)
async def create_meeting(payload: MeetingCreate, session=Depends(get_session)):  # noqa: B008
    repo = MeetingRepository(session)
    meeting = await repo.add(
        project_id=payload.project_id,
        title=payload.title,
        transcript=payload.transcript,
        participants=payload.participants,
    )
    await session.commit()
    return MeetingOut.from_orm_obj(meeting)


@router.get("/{meeting_id}", response_model=MeetingOut)
async def get_meeting(meeting_id: int, session=Depends(get_session)):  # noqa: B008
    repo = MeetingRepository(session)
    meeting = await repo.get(meeting_id)
    if meeting is None:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return MeetingOut.from_orm_obj(meeting)


@router.post("/{meeting_id}/summarize")
async def summarize_meeting(meeting_id: int, session=Depends(get_session)):  # noqa: B008
    meeting_repo = MeetingRepository(session)
    runs_repo = PipelineRunRepository(session)
    service = PipelineService(docs_repo=None, runs_repo=runs_repo)  # type: ignore[arg-type]
    try:
        output = await service.summarize_meeting(meeting_repo, meeting_id)
    except ValueError as err:  # B904: explicit chaining
        raise HTTPException(status_code=404, detail="Meeting not found") from err
    await session.commit()
    return output
