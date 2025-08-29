"""Document endpoints with Redis caching."""
from __future__ import annotations

from typing import Any, cast

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from hlpr.core.cache_manager import document_cache, summarization_cache
from hlpr.db.dependencies import get_session
from hlpr.db.repositories import DocumentRepository, PipelineRunRepository
from hlpr.services.pipelines import PipelineService

router = APIRouter(prefix="/documents", tags=["documents"])


class DocumentCreate(BaseModel):
    project_id: int
    title: str
    content: str


class DocumentOut(BaseModel):
    id: int
    project_id: int
    title: str
    content: str

    @classmethod
    def from_orm_obj(cls, document: Any) -> DocumentOut:
        return cls(
            id=document.id,
            project_id=document.project_id,
            title=document.title,
            content=document.content,
        )


@router.post("/")
async def create_document(
    document: DocumentCreate, session: AsyncSession = Depends(get_session)  # noqa: B008
) -> dict[str, Any]:
    repo = DocumentRepository(session)
    document_record = await repo.add(
        project_id=document.project_id,
        title=document.title,
        content=document.content,
    )
    await session.commit()
    
    result = {
        "id": document_record.id,
        "title": document_record.title,
        "content": document_record.content,
        "created_at": document_record.created_at.isoformat() if document_record.created_at else None,
    }
    
    # Warm cache with the new document data
    cache_key = f"document:{document_record.id}"
    await document_cache.set(cache_key, result)
    
    return result


@router.get("/{document_id}", response_model=DocumentOut)
async def get_document(
    document_id: int, session: AsyncSession = Depends(get_session)  # noqa: B008
) -> DocumentOut:
    # Try to get from cache first
    cache_key = f"document:{document_id}"
    cached_document = await document_cache.get(cache_key)
    
    if cached_document:
        return DocumentOut(**cached_document)
    
    # Get from database if not cached
    repo = DocumentRepository(session)
    document = await repo.get(document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    
    document_out = DocumentOut.from_orm_obj(document)
    
    # Cache the result
    await document_cache.set(cache_key, document_out.model_dump())
    
    return document_out


@router.get("/project/{project_id}")
async def list_project_documents(
    project_id: int, session: AsyncSession = Depends(get_session)  # noqa: B008
) -> list[dict[str, Any]]:
    # Try to get from cache first
    cache_key = f"project_documents:{project_id}"
    cached_documents = await document_cache.get(cache_key)
    
    if cached_documents:
        # Cast cached result to list[dict[str, Any]]
        return cast(list[dict[str, Any]], cached_documents)
    
    # Get from database if not cached
    repo = DocumentRepository(session)
    documents = await repo.list_by_project(project_id)
    
    result = []
    for doc in documents:
        result.append({
            "id": doc.id,
            "title": doc.title,
            "content": doc.content,
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
        })
    
    # Cache the result
    await document_cache.set(cache_key, result)
    
    return result


@router.post("/{document_id}/summarize")
async def summarize_document(
    document_id: int, session: AsyncSession = Depends(get_session)  # noqa: B008
) -> dict[str, Any]:
    # Try to get from cache first
    cache_key = f"document_summary:{document_id}"
    cached_summary = await summarization_cache.get(cache_key)
    
    if cached_summary:
        return cached_summary  # type: ignore[no-any-return]
    
    # Generate summary if not cached
    docs_repo = DocumentRepository(session)
    runs_repo = PipelineRunRepository(session)
    service = PipelineService(docs_repo, runs_repo)
    
    try:
        output = await service.summarize_document(document_id)
        # Cast output to dict[str, Any] - service should return dict
        output = cast(dict[str, Any], output)
    except ValueError as err:  # B904: explicit chaining
        raise HTTPException(status_code=404, detail="Document not found") from err
    
    await session.commit()
    
    # Cache the summary result
    await summarization_cache.set(cache_key, output)
    
    return output