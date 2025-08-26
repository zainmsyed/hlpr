"""Clean test: verify pipeline sends the meeting transcript to DSPy program.

This file intentionally keeps a single, focused async pytest that:
 - creates tiny dummy repos for meetings and run tracking
 - injects a FakeProgram onto pipeline._dspy_program
 - runs the pipeline and asserts the fake program received the transcript
"""
from __future__ import annotations

import pytest

from hlpr.pipelines.meeting_summarization import MeetingSummarizationPipeline


class DummyMeetingRepo:
    def __init__(self, transcript: str):
        self._transcript = transcript

    async def get(self, meeting_id: int):
        return type("M", (), {"id": meeting_id, "transcript": self._transcript})


class DummyRunsRepo:
    async def start(self, name: str, descriptor: str):
        return "run-1"

    async def complete(self, run_id: str, output: dict):
        # noop
        return None


@pytest.mark.asyncio
async def test_mipro_prompt_injected():
    # Use a small, deterministic transcript that contains the expected speaker markers
    content = (
        "10:00:00 - Meeting Start\n"
        "Priya (P): Okay team, let's get started.\n"
        "Mark (M): The homepage design is 100% signed off.\n"
        "Sarah (S): I'll implement the components.\n"
    )

    captured: dict[str, str] = {}

    class FakeProgram:
        def __call__(self, transcript: str):
            captured["transcript"] = transcript
            return {"summary": "fake summary", "action_items": ["fake action"]}

    meetings_repo = DummyMeetingRepo(content)
    runs_repo = DummyRunsRepo()
    pipeline = MeetingSummarizationPipeline(meetings_repo, runs_repo)
    pipeline._dspy_program = FakeProgram()

    out = await pipeline.run(1)

    assert "transcript" in captured, "DSPy program was not called"
    captured_transcript = captured["transcript"]
    assert (
        "Priya (P):" in captured_transcript or "Priya:" in captured_transcript
    ), "Expected 'Priya' to be present in the transcript passed to DSPy"
    assert (
        "Mark (M):" in captured_transcript or "Mark:" in captured_transcript
    ), "Expected 'Mark' to be present in the transcript passed to DSPy"
    assert out["summary"] == "fake summary"
