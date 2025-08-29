"""Service layer orchestrating DSPy pipelines with repositories."""
from __future__ import annotations

from typing import Any, cast

from hlpr.core.cache_manager import summarization_cache
from hlpr.pipelines.interfaces import (
    DocumentRepositoryProtocol,
    MeetingRepositoryProtocol,
    PipelineRunRepositoryProtocol,
)
from hlpr.pipelines.meeting_summarization import MeetingSummarizationPipeline
from hlpr.pipelines.summarization import SummarizationPipeline


class PipelineService:
    def __init__(
        self,
        docs_repo: DocumentRepositoryProtocol,
        runs_repo: PipelineRunRepositoryProtocol,
    ) -> None:
        self._docs_repo = docs_repo
        self._runs_repo = runs_repo

    async def summarize_document(self, document_id: int) -> dict[str, Any]:
        # Try to get from cache first
        cache_key = f"document_summary:{document_id}"
        cached_result = await summarization_cache.get(cache_key)
        
        if cached_result:
            return cached_result  # type: ignore[no-any-return]
        
        # Generate summary if not cached
        pipeline: SummarizationPipeline = SummarizationPipeline(self._docs_repo, self._runs_repo)
        result = await pipeline.run(document_id)
        
        # Cast result to dict[str, Any] - pipeline should return dict
        result = cast(dict[str, Any], result)
        
        # Cache the result
        await summarization_cache.set(cache_key, result)
        
        return result

    async def summarize_meeting(self, meeting_id: int) -> dict[str, Any]:
        """Summarize a single meeting using the meeting summarization pipeline.

        Args:
            meeting_id: The ID of the meeting to summarize

        Returns:
            Dictionary containing the summarization results
        """
        # Import here to avoid circular imports
        from hlpr.db.repositories import MeetingRepository

        # Create meeting repository instance
        meeting_repo = MeetingRepository(self._docs_repo.session if hasattr(self._docs_repo, 'session') else None)

        return await self._run_meeting_summarization(meeting_repo, meeting_id)

    async def _run_meeting_summarization(
        self,
        meeting_repo: MeetingRepositoryProtocol,
        meeting_id: int,
    ) -> dict[str, Any]:
        # Try to get from cache first
        cache_key = f"meeting_summary:{meeting_id}"
        cached_result = await summarization_cache.get(cache_key)
        
        if cached_result:
            return cached_result  # type: ignore[no-any-return]
        
        # Generate summary if not cached
        pipeline = MeetingSummarizationPipeline(meeting_repo, self._runs_repo)
        result = await pipeline.run(meeting_id)
        
        # Cast result to dict[str, Any] - pipeline should return dict
        result = cast(dict[str, Any], result)
        
        # Cache the result
        await summarization_cache.set(cache_key, result)
        
        return result
