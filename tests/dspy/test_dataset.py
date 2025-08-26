"""Test dataset loading utilities."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from hlpr.dspy.dataset import MeetingExample, load_meeting_examples


def test_load_meeting_examples(tmp_path: Path) -> None:
    """Test that dataset loader correctly parses and filters JSONL examples."""
    # Create test data file
    test_data = [
        {
            "id": "1",
            "meeting_transcript": "Alice: We need to complete task A. Bob: I'll handle it.",
            "gold_summary": "Alice assigned task A to Bob.",
            "action_items": ["Complete task A"],
            "owners": ["Bob"],
            "verified": True,
            "synthetic_strategy": "extractive",
        },
        {
            "id": "2",
            "meeting_transcript": "Charlie: Review the proposal.",
            "gold_summary": "Charlie will review proposal.",
            "action_items": ["Review proposal"],
            "owners": ["Charlie"],
            "verified": False,
            "synthetic_strategy": "fabricated",
        },
    ]
    
    test_file = tmp_path / "test_meetings.jsonl"
    with test_file.open("w") as f:
        for item in test_data:
            f.write(json.dumps(item) + "\n")
    
    # Test verified-only loading (default)
    examples = load_meeting_examples(test_file, include_unverified=False)
    assert len(examples) == 1
    assert examples[0].id == "1"
    assert examples[0].verified is True
    assert "Alice" in examples[0].transcript
    
    # Test including unverified
    all_examples = load_meeting_examples(test_file, include_unverified=True)
    assert len(all_examples) == 2
    assert all_examples[1].id == "2"
    assert all_examples[1].verified is False
    
    # Test limit parameter
    limited = load_meeting_examples(test_file, include_unverified=True, limit=1)
    assert len(limited) == 1


def test_meeting_example_fields() -> None:
    """Test MeetingExample dataclass structure."""
    example = MeetingExample(
        id="test",
        transcript="Test transcript",
        gold_summary="Test summary",
        action_items=["Task 1", "Task 2"],
        owners=["Alice", "Bob"],
        verified=True,
        synthetic_strategy="extractive",
        summary_type="detailed",
    )
    
    assert example.id == "test"
    assert len(example.action_items) == 2
    assert example.verified is True
