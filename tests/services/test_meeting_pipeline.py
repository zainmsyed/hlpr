"""Test meeting summarization pipeline end-to-end."""
from __future__ import annotations

import pytest

from hlpr.db.base import get_session_factory, init_models
from hlpr.db.repositories import MeetingRepository, PipelineRunRepository
from hlpr.pipelines.meeting_summarization import MeetingSummarizationPipeline


@pytest.mark.asyncio
async def test_meeting_pipeline_sqlite():
    await init_models(drop=True)
    session_factory = get_session_factory()
    async with session_factory() as session:  # type: ignore[call-arg]
        meetings = MeetingRepository(session)
        runs = PipelineRunRepository(session)

        mtg = await meetings.add(
            project_id=1,
            title="Sprint Planning",
            transcript="""Alice will finalize the API spec by Friday. We decided to postpone the refactor. ACTION: Update the roadmap.""",
            participants=["alice", "bob"],
        )
        await session.commit()

        pipeline = MeetingSummarizationPipeline(meetings, runs)
        output = await pipeline.run(mtg.id)

        assert output["meeting_id"] == mtg.id
        assert "summary" in output
        assert len(output["action_items"]) >= 1
        assert any("decided" in d["decision"].lower() for d in output["decisions"])  # simple check

        pr = await runs.get(1)
        assert pr is not None and pr.status == "completed"
