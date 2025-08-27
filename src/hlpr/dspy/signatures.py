"""DSPy Signatures for meeting processing (summary + action items + decisions)."""
from __future__ import annotations

import dspy


class MeetingSummary(dspy.Signature):  # type: ignore[misc]
    """Summarize the meeting transcript in 3 concise sentences focusing on key outcomes. Then give a summary of the meeting organized into topics with relevant bullets underneath.

    transcript -> summary
    """

    transcript: str = dspy.InputField()
    summary: str = dspy.OutputField()


class ExtractActionItems(dspy.Signature):  # type: ignore[misc]
    """Extract concrete action items; each should be a short imperative or assignment.

    transcript -> action_items
    """

    transcript: str = dspy.InputField()
    action_items: list[str] = dspy.OutputField()


class ExtractDecisions(dspy.Signature):  # type: ignore[misc]
    """List explicit decisions or approvals made during the meeting.

    transcript -> decisions
    """

    transcript: str = dspy.InputField()
    decisions: list[str] = dspy.OutputField()
