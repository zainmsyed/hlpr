"""FastAPI dependency helpers for repositories."""
from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from .base import get_session
from .repositories import DocumentRepository, PipelineRunRepository


def get_document_repo(
    session: AsyncSession = Depends(get_session),  # noqa: B008 - FastAPI DI
) -> DocumentRepository:
    return DocumentRepository(session)

def get_pipeline_run_repo(
    session: AsyncSession = Depends(get_session),  # noqa: B008 - FastAPI DI
) -> PipelineRunRepository:
    return PipelineRunRepository(session)
