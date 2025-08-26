"""Meeting summarization & extraction pipeline.

Includes heuristic extractor plus optional DSPy opti        try:  # pragma: no cover - environment dependent
            import dspy

            from hlpr.dspy.signatures import ExtractActionItems, MeetingSummary

            class _Prog(dspy.Module):  # type: ignore[misc]
                def __init__(self) -> None:
                    super().__init__()
                    self.summarizer = dspy.ChainOfThought(MeetingSummary)
                    self.action_items = dspy.ChainOfThought(ExtractActionItems)

                def forward(self, transcript: str) -> dict[str, Any]:  # type: ignore[override]
                    s = self.summarizer(transcript=transcript).summary
                    a = self.action_items(transcript=transcript).action_items
                    return {"summary": s, "action_items": a}

            return _Prog()ifact fallback.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hlpr.pipelines.interfaces import (
    MeetingRepositoryProtocol,
    PipelineRunRepositoryProtocol,
)


@dataclass(slots=True)
class MeetingOutput:
    meeting_id: int
    summary: str
    action_items: list[dict[str, str]]
    decisions: list[dict[str, str]]
    next_steps: list[str]

    def to_dict(self) -> dict[str, Any]:  # convenience
        return {
            "meeting_id": self.meeting_id,
            "summary": self.summary,
            "action_items": self.action_items,
            "decisions": self.decisions,
            "next_steps": self.next_steps,
        }


class HeuristicMeetingExtractor:
    action_item_patterns = [
        re.compile(r"^(?:-\s*)?(?:ACTION|TODO)[:\-]\s*(.+)", re.IGNORECASE),
        re.compile(r"^(?:-\s*)?@?(\w+)\s+will\s+(.*)", re.IGNORECASE),
    ]
    decision_patterns = [
        re.compile(r"\bdecided\b(.+)", re.IGNORECASE),
        re.compile(r"\bapproved\b(.+)", re.IGNORECASE),
    ]

    def extract(self, transcript: str) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
        action_items: list[dict[str, str]] = []
        decisions: list[dict[str, str]] = []
        for line in transcript.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            # Action items
            for pat in self.action_item_patterns:
                m = pat.search(stripped)
                if m:
                    if pat.pattern.startswith("^(?:-\\s*)?@?(\\w+)") and len(m.groups()) >= 2:
                        assignee, task = m.group(1), m.group(2)
                        action_items.append({"assignee": assignee, "task": task.strip()})
                    else:
                        task = m.group(1)
                        action_items.append({"task": task.strip()})
                    break
            # Decisions
            for pat in self.decision_patterns:
                m = pat.search(stripped)
                if m:
                    decisions.append({"decision": m.group(0).strip()})
                    break
        return action_items, decisions

    def summarize(self, transcript: str, max_sentences: int = 3) -> str:
        sentences = re.split(r"(?<=[.!?])\s+", transcript.strip())
        return " ".join(sentences[:max_sentences])


class MeetingSummarizationPipeline:
    def __init__(
        self,
        meetings_repo: MeetingRepositoryProtocol,
        runs_repo: PipelineRunRepositoryProtocol,
    ) -> None:
        self.meetings = meetings_repo
        self.runs = runs_repo
        self.extractor = HeuristicMeetingExtractor()
        self._optimized_artifact: dict[str, Any] | None = self._load_artifact()
        self._dspy_program = self._init_dspy_program()

    def _load_artifact(self) -> dict[str, Any] | None:
        path = Path("artifacts/meeting/optimized_program.json")
        if path.exists():  # pragma: no branch
            try:
                artifact: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
                return artifact
            except Exception:  # pragma: no cover
                return None
        return None

    def _init_dspy_program(self) -> Any | None:  # lazy import to avoid hard dependency if unused
        if not self._optimized_artifact:
            return None
        try:  # pragma: no cover - environment dependent
            import dspy

            from hlpr.dspy.signatures import ExtractActionItems, MeetingSummary

            class _Prog(dspy.Module):  # type: ignore[misc]
                def __init__(self) -> None:
                    super().__init__()
                    self.summarizer = dspy.ChainOfThought(MeetingSummary)
                    self.action_items = dspy.ChainOfThought(ExtractActionItems)

                def forward(self, transcript: str) -> dict[str, Any]:  # type: ignore[override]
                    s = self.summarizer(transcript=transcript).summary
                    a = self.action_items(transcript=transcript).action_items
                    return {"summary": s, "action_items": a}

            return _Prog()
        except Exception:
            return None

    async def run(self, meeting_id: int) -> dict[str, Any]:
        run_id = await self.runs.start("meeting_summarization", f"meeting:{meeting_id}")
        meeting = await self.meetings.get(meeting_id)
        if meeting is None:
            raise ValueError("Meeting not found")
        transcript: str = meeting.transcript
        if self._dspy_program is not None:
            try:
                dspy_out = self._dspy_program(transcript=transcript)
                summary = dspy_out.get("summary") or ""
                action_items = [{"task": t} for t in dspy_out.get("action_items", [])]
                decisions: list[dict[str, str]] = []  # signature not yet integrated
            except Exception:  # fallback to heuristic
                action_items, decisions = self.extractor.extract(transcript)
                summary = self.extractor.summarize(transcript)
        else:
            action_items, decisions = self.extractor.extract(transcript)
            summary = self.extractor.summarize(transcript)
        next_steps = [ai.get("task", "") for ai in action_items][:5]
        output = MeetingOutput(
            meeting_id=meeting_id,
            summary=summary,
            action_items=action_items,
            decisions=decisions,
            next_steps=next_steps,
        )
        await self.runs.complete(run_id, output.to_dict())
        return output.to_dict()
