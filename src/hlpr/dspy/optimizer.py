"""Skeleton optimization (MIPRO-like) for meeting pipeline using DSPy.

This is a lightweight loop that evaluates simple signatures; later can be replaced by real MIPRO.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import dspy

from .dataset import load_meeting_examples
from .metrics import list_exact_match, summary_token_overlap
from .signatures import ExtractActionItems, MeetingSummary


@dataclass(slots=True)
class OptimizerConfig:
    data_path: str = "documents/training-data/meetings.txt"
    include_unverified: bool = False
    iters: int = 3
    artifact_dir: str = "artifacts/meeting"
    model: str | None = None  # e.g., "ollama/llama3" or OpenAI model name


def _init_model(model: str | None) -> None:
    """Initialize DSPy with the specified model (default: gpt-3.5-turbo)."""
    chosen = model or "gpt-3.5-turbo"
    
    # Ollama support via DSPy LM client
    if "ollama/" in chosen:
        try:
            # Extract model name (e.g., "ollama/gemma3" -> "gemma3")
            model_name = chosen.split("/")[-1]
            # Use the ollama/model_name format that litellm expects
            lm = dspy.LM(
                model=f"ollama/{model_name}",
                api_base="http://localhost:11434"
            )
            dspy.configure(lm=lm)
            return
        except Exception:  # pragma: no cover
            pass
    
    # Fallback to OpenAI-compatible models via DSPy LM
    lm = dspy.LM(model=chosen)
    dspy.configure(lm=lm)


class MeetingProgram(dspy.Module):  # type: ignore[misc]
    def __init__(self) -> None:
        super().__init__()
        self.summarizer = dspy.ChainOfThought(MeetingSummary)
        self.action_items = dspy.ChainOfThought(ExtractActionItems)

    def forward(self, transcript: str) -> dict[str, Any]:
        summary = self.summarizer(transcript=transcript).summary
        actions = self.action_items(transcript=transcript).action_items
        return {"summary": summary, "action_items": actions}


def optimize(config: OptimizerConfig) -> dict[str, Any]:
    _init_model(config.model)
    examples = load_meeting_examples(
        config.data_path, include_unverified=config.include_unverified
    )
    if not examples:
        raise ValueError("No examples loaded for optimization")

    program = MeetingProgram()
    best_score = -1.0
    best_artifact: dict[str, Any] | None = None

    for i in range(config.iters):
        summary_f1_total = 0.0
        action_f1_total = 0.0
        for ex in examples:
            out = program(transcript=ex.transcript)
            sm = summary_token_overlap(out["summary"], ex.gold_summary)
            am = list_exact_match(out["action_items"], ex.action_items)
            summary_f1_total += sm.f1
            action_f1_total += am.f1
        avg_summary_f1 = summary_f1_total / len(examples)
        avg_action_f1 = action_f1_total / len(examples)
        composite = (avg_summary_f1 + avg_action_f1) / 2.0
        if composite > best_score:
            best_score = composite
            best_artifact = {
                "iteration": i,
                "avg_summary_f1": avg_summary_f1,
                "avg_action_f1": avg_action_f1,
                "composite": composite,
                "model": config.model,
                "program_repr": str(program),
            }

    artifact_dir = Path(config.artifact_dir)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = artifact_dir / "optimized_program.json"
    with artifact_path.open("w", encoding="utf-8") as fh:
        json.dump(best_artifact, fh, indent=2)
    return {
        "best_score": best_score,
        "artifact_path": str(artifact_path),
        "iterations": config.iters,
        "num_examples": len(examples),
    }
