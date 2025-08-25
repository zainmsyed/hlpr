"""Test summarization pipeline end-to-end with in-memory SQLite DB."""
from __future__ import annotations

import json

import pytest

from hlpr.db.base import get_session_factory, init_models
from hlpr.db.repositories import DocumentRepository, PipelineRunRepository
from hlpr.services.pipelines import PipelineService


@pytest.mark.asyncio
async def test_summarization_pipeline_sqlite(tmp_path):
    # Override settings dynamically by patching environment if needed
    # Ensure tables created
    await init_models(drop=True)

    session_factory = get_session_factory()
    async with session_factory() as session:  # type: ignore[call-arg]
        docs = DocumentRepository(session)
        runs = PipelineRunRepository(session)

        # Create a doc
        doc = await docs.add(project_id=1, title="Test", content="This is a longish document body for summarization testing.")
        await session.commit()

        service = PipelineService(docs, runs)
        result = await service.summarize_document(doc.id)

        assert result["document_id"] == doc.id
        assert "summary" in result
        # Verify run persisted
        pr = await runs.get(1)
        assert pr is not None
        assert pr.status == "completed"
        assert pr.output_json is not None
        parsed = json.loads(pr.output_json)
        assert parsed["summary"] == result["summary"]
