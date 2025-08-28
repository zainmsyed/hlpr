"""API tests for meeting endpoints."""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from hlpr.db.base import init_models
from hlpr.main import app


@pytest.mark.asyncio
async def test_create_and_summarize_meeting():
    await init_models(drop=True)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        create_resp = await ac.post(
            "/api/meetings/",
            json={
                "project_id": 1,
                "title": "Sprint Planning",
                "transcript": "Alice will finalize the API spec by Friday. We decided to postpone the refactor. ACTION: Update the roadmap.",
                "participants": ["alice", "bob"],
            },
        )
        assert create_resp.status_code == 200, create_resp.text
        meeting_id = create_resp.json()["id"]

        summarize_resp = await ac.post(f"/api/meetings/{meeting_id}/summarize")
        assert summarize_resp.status_code == 200, summarize_resp.text
        data = summarize_resp.json()
        assert data["meeting_id"] == meeting_id
        assert "summary" in data
        assert isinstance(data["action_items"], list)
