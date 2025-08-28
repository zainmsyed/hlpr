"""Shared DSPy program classes for meeting processing.

This module contains reusable DSPy program implementations that can be used
across different parts of the application (optimization, inference, etc.).
"""
from __future__ import annotations

import dspy

from .signatures import ExtractActionItems, MeetingSummary


class MeetingProgram(dspy.Module):  # type: ignore[misc]
    """DSPy program for processing meeting transcripts.

    This program combines meeting summarization and action item extraction
    into a single, reusable module that can be optimized and deployed.
    """

    def __init__(self) -> None:
        super().__init__()
        self.summarizer = dspy.ChainOfThought(MeetingSummary)
        self.action_items = dspy.ChainOfThought(ExtractActionItems)

    def forward(self, transcript: str) -> dict[str, str | list[str]]:
        """Process a meeting transcript to extract summary and action items.

        Args:
            transcript: The meeting transcript text

        Returns:
            Dictionary containing:
            - summary: Meeting summary text
            - action_items: List of action items
        """
        summary = self.summarizer(transcript=transcript).summary
        actions = self.action_items(transcript=transcript).action_items
        return {"summary": summary, "action_items": actions}