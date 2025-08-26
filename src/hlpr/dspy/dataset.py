"""Dataset loading utilities for meeting optimization examples."""
from __future__ import annotations

import json
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class MeetingExample:
    id: str
    transcript: str
    gold_summary: str
    action_items: list[str]
    owners: list[str]
    verified: bool
    synthetic_strategy: str | None = None
    summary_type: str | None = None


def load_meeting_examples(
    path: str | Path,
    include_unverified: bool = False,
    limit: int | None = None,
) -> list[MeetingExample]:
    p = Path(path)
    if not p.exists():  # pragma: no cover
        raise FileNotFoundError(p)
    examples: list[MeetingExample] = []
    with p.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if not include_unverified and not obj.get("verified", False):
                continue
            examples.append(
                MeetingExample(
                    id=str(obj.get("id")),
                    transcript=obj.get("meeting_transcript", ""),
                    gold_summary=obj.get("gold_summary", ""),
                    action_items=list(obj.get("action_items", [])),
                    owners=list(obj.get("owners", [])),
                    verified=bool(obj.get("verified", False)),
                    synthetic_strategy=obj.get("synthetic_strategy"),
                    summary_type=obj.get("summary_type"),
                )
            )
            if limit and len(examples) >= limit:
                break
    return examples


def iter_batches(seq: Sequence[MeetingExample], batch_size: int) -> Iterator[Sequence[MeetingExample]]:
    for i in range(0, len(seq), batch_size):
        yield seq[i : i + batch_size]
