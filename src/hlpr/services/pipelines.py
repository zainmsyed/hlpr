"""Service layer orchestrating DSPy pipelines with repositories."""
from __future__ import annotations

from typing import Any

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
        pipeline: SummarizationPipeline = SummarizationPipeline(self._docs_repo, self._runs_repo)
        result: dict[str, Any] = await pipeline.run(document_id)
        return result

    async def summarize_meeting(
        self,
        meeting_repo: MeetingRepositoryProtocol,
        meeting_id: int,
    ) -> dict[str, Any]:
        pipeline = MeetingSummarizationPipeline(meeting_repo, self._runs_repo)
        return await pipeline.run(meeting_id)
