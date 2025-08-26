"""Repository implementations using SQLAlchemy async sessions."""
from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Document, Meeting, PipelineRun


class DocumentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, doc_id: int) -> Document | None:
        result = await self.session.execute(select(Document).where(Document.id == doc_id))
        return result.scalar_one_or_none()

    async def list_by_project(self, project_id: int, limit: int = 50) -> Sequence[Document]:
        result = await self.session.execute(
            select(Document).where(Document.project_id == project_id).limit(limit)
        )
        return list(result.scalars())

    async def add(self, project_id: int, title: str, content: str) -> Document:
        doc = Document(project_id=project_id, title=title, content=content)
        self.session.add(doc)
        await self.session.flush()  # assign id
        return doc


class PipelineRunRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def start(self, pipeline: str, input_ref: str) -> int:
        run = PipelineRun(pipeline_name=pipeline, input_ref=input_ref, status="started")
        self.session.add(run)
        await self.session.flush()
        return run.id

    async def complete(self, run_id: int, output: dict[str, Any]) -> None:
        await self.session.execute(
            update(PipelineRun)
            .where(PipelineRun.id == run_id)
            .values(status="completed", output_json=json.dumps(output))
        )

    async def get(self, run_id: int) -> PipelineRun | None:
        result = await self.session.execute(select(PipelineRun).where(PipelineRun.id == run_id))
        return result.scalar_one_or_none()


class MeetingRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, meeting_id: int) -> Meeting | None:
        result = await self.session.execute(select(Meeting).where(Meeting.id == meeting_id))
        return result.scalar_one_or_none()

    async def add(
        self,
        project_id: int,
        title: str,
        transcript: str,
        participants: list[str] | None = None,
    ) -> Meeting:
        participants_csv = ",".join(participants) if participants else None
        meeting = Meeting(
            project_id=project_id,
            title=title,
            transcript=transcript,
            participants=participants_csv,
        )
        self.session.add(meeting)
        await self.session.flush()
        return meeting
