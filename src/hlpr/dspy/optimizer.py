"""Advanced MIPRO optimization pipeline for meeting processing using DSPy.

This implements multiple optimization strategies including MIPROv2, COPRO, and BootstrapFewShot
with comprehensive evaluation and artifact management.
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

logger = logging.getLogger(__name__)

import dspy
from dspy.teleprompt import COPRO, BootstrapFewShot, BootstrapFewShotWithRandomSearch, MIPROv2

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
    optimizer: Literal["mipro", "copro", "bootstrap", "bootstrap_random"] = "mipro"
    max_bootstrapped_demos: int = 4
    max_labeled_demos: int = 16
    eval_kwargs: dict[str, Any] | None = None


def _init_model(model: str | None) -> None:
    """Initialize DSPy with the specified model (default: gpt-3.5-turbo)."""
    chosen = model or "gpt-3.5-turbo"
    
    # Ollama support via DSPy LM client
    if "ollama/" in chosen:
        try:
            # Extract model name (e.g., "ollama/gemma3" -> "gemma3")
            model_name = chosen.split("/")[-1]
            # Use host.docker.internal for Docker container or localhost for local
            api_base = "http://host.docker.internal:11434" if Path("/.dockerenv").exists() else "http://localhost:11434"
            # Use the ollama/model_name format that litellm expects
            lm = dspy.LM(
                model=f"ollama/{model_name}",
                api_base=api_base
            )
            dspy.configure(lm=lm)
            print(f"✅ Configured DSPy with Ollama model: {model_name} at {api_base}")
            return
        except Exception as e:  # pragma: no cover
            print(f"⚠️ Failed to configure Ollama model {chosen}: {e}")
            print("🔄 Falling back to OpenAI model...")
    
    # Fallback to OpenAI-compatible models via DSPy LM
    lm = dspy.LM(model=chosen)
    dspy.configure(lm=lm)
    print(f"✅ Configured DSPy with model: {chosen}")


class MeetingProgram(dspy.Module):  # type: ignore[misc]
    def __init__(self) -> None:
        super().__init__()
        self.summarizer = dspy.ChainOfThought(MeetingSummary)
        self.action_items = dspy.ChainOfThought(ExtractActionItems)

    def forward(self, transcript: str) -> dict[str, Any]:
        summary = self.summarizer(transcript=transcript).summary
        actions = self.action_items(transcript=transcript).action_items
        return {"summary": summary, "action_items": actions}


def _convert_to_dspy_examples(meeting_examples: list) -> list[dspy.Example]:
    """Convert MeetingExample objects to DSPy Example format."""
    dspy_examples = []
    
    for ex in meeting_examples:
        # Create DSPy Example with inputs and expected outputs
        dspy_example = dspy.Example(
            transcript=ex.transcript,
            summary=ex.gold_summary,
            action_items=ex.action_items
        ).with_inputs("transcript")
        
        dspy_examples.append(dspy_example)
    
    return dspy_examples


def _create_metric() -> callable:
    """Create a composite metric for evaluation."""
    def meeting_metric(gold, pred, trace=None):
        # Handle different gold formats
        if hasattr(gold, 'summary') and hasattr(gold, 'action_items'):
            gold_summary = gold.summary
            gold_actions = gold.action_items
        elif isinstance(gold, dict):
            gold_summary = gold.get('summary', '')
            gold_actions = gold.get('action_items', [])
        else:
            return 0.0
        
        # Handle prediction format
        if isinstance(pred, dict):
            pred_summary = pred.get('summary', '')
            pred_actions = pred.get('action_items', [])
        elif hasattr(pred, 'summary') and hasattr(pred, 'action_items'):
            pred_summary = pred.summary
            pred_actions = pred.action_items
        else:
            return 0.0
        
        # Calculate metrics
        summary_score = summary_token_overlap(pred_summary, gold_summary).f1
        action_score = list_exact_match(pred_actions, gold_actions).f1
        
        # Composite score
        return (summary_score + action_score) / 2.0
    
    return meeting_metric


def _optimize_with_mipro(program: MeetingProgram, trainset: list, valset: list, config: OptimizerConfig) -> tuple[Any, dict]:
    """Optimize using MIPROv2."""
    print("🔧 Starting MIPROv2 optimization...")
    
    # Initialize MIPROv2 optimizer
    optimizer = MIPROv2(
        metric=_create_metric(),
        auto="medium",  # Automatic optimization level
        max_bootstrapped_demos=config.max_bootstrapped_demos,
        max_labeled_demos=config.max_labeled_demos,
        init_temperature=0.7,
        verbose=True
    )
    
    # Run optimization
    start_time = time.time()
    optimized_program = optimizer.compile(program, trainset=trainset, valset=valset)
    optimization_time = time.time() - start_time
    
    results = {
        "optimizer": "mipro",
        "optimization_time": optimization_time,
        "max_bootstrapped_demos": config.max_bootstrapped_demos,
        "max_labeled_demos": config.max_labeled_demos,
        "trainset_size": len(trainset),
        "valset_size": len(valset)
    }
    
    return optimized_program, results


def _optimize_with_copro(program: MeetingProgram, trainset: list, config: OptimizerConfig) -> tuple[Any, dict]:
    """Optimize using COPRO (Collaborative Prompt Optimization)."""
    print("🔧 Starting COPRO optimization...")
    
    # Initialize COPRO optimizer
    optimizer = COPRO(
        metric=_create_metric(),
        breadth=10,
        depth=config.iters,
        init_temperature=1.4
    )
    
    # Run optimization
    start_time = time.time()
    optimized_program = optimizer.compile(program, trainset=trainset)
    optimization_time = time.time() - start_time
    
    results = {
        "optimizer": "copro",
        "optimization_time": optimization_time,
        "breadth": 10,
        "depth": config.iters,
        "trainset_size": len(trainset)
    }
    
    return optimized_program, results


def _optimize_with_bootstrap(program: MeetingProgram, trainset: list, config: OptimizerConfig, random_search: bool = False) -> tuple[Any, dict]:
    """Optimize using BootstrapFewShot or BootstrapFewShotWithRandomSearch."""
    optimizer_name = "bootstrap_random" if random_search else "bootstrap"
    print(f"🔧 Starting {optimizer_name} optimization...")
    
    # Choose optimizer
    if random_search:
        optimizer = BootstrapFewShotWithRandomSearch(
            metric=_create_metric(),
            max_bootstrapped_demos=config.max_bootstrapped_demos,
            max_labeled_demos=config.max_labeled_demos,
            num_candidate_programs=config.iters
        )
    else:
        optimizer = BootstrapFewShot(
            metric=_create_metric(),
            max_bootstrapped_demos=config.max_bootstrapped_demos,
            max_labeled_demos=config.max_labeled_demos
        )
    
    # Run optimization
    start_time = time.time()
    optimized_program = optimizer.compile(program, trainset=trainset)
    optimization_time = time.time() - start_time
    
    results = {
        "optimizer": optimizer_name,
        "optimization_time": optimization_time,
        "max_bootstrapped_demos": config.max_bootstrapped_demos,
        "max_labeled_demos": config.max_labeled_demos,
        "trainset_size": len(trainset)
    }
    
    return optimized_program, results


def _evaluate_program(program: Any, examples: list) -> dict[str, float]:
    """Evaluate the optimized program on examples."""
    print("📊 Evaluating optimized program...")
    
    summary_scores = []
    action_scores = []
    
    for ex in examples:
        try:
            output = program(transcript=ex.transcript)
            
            # Calculate individual metrics
            summary_score = summary_token_overlap(output["summary"], ex.gold_summary).f1
            action_score = list_exact_match(output["action_items"], ex.action_items).f1
            
            summary_scores.append(summary_score)
            action_scores.append(action_score)
        except Exception as e:
            print(f"⚠️  Evaluation error for example: {e}")
            summary_scores.append(0.0)
            action_scores.append(0.0)
    
    return {
        "avg_summary_f1": sum(summary_scores) / len(summary_scores) if summary_scores else 0.0,
        "avg_action_f1": sum(action_scores) / len(action_scores) if action_scores else 0.0,
        "composite_f1": (sum(summary_scores) + sum(action_scores)) / (2 * len(examples)) if examples else 0.0,
        "num_examples": len(examples)
    }


def optimize(config: OptimizerConfig) -> dict[str, Any]:
    """Run the complete MIPRO optimization pipeline."""
    print(f"🚀 Starting optimization with {config.optimizer} strategy...")
    
    # Initialize model
    _init_model(config.model)
    
    # Load examples
    examples = load_meeting_examples(
        config.data_path, include_unverified=config.include_unverified
    )
    if not examples:
        raise ValueError("No examples loaded for optimization")
    
    print(f"📚 Loaded {len(examples)} examples for optimization")
    
    # Convert to DSPy format
    dspy_examples = _convert_to_dspy_examples(examples)
    
    # Split into train/validation sets (80/20 split)
    split_idx = int(0.8 * len(dspy_examples))
    trainset = dspy_examples[:split_idx]
    valset = dspy_examples[split_idx:] if split_idx < len(dspy_examples) else dspy_examples[-1:]
    
    print(f"📊 Train set: {len(trainset)} examples, Validation set: {len(valset)} examples")
    
    # Initialize program
    program = MeetingProgram()
    
    # Run optimization based on strategy
    if config.optimizer == "mipro":
        optimized_program, opt_results = _optimize_with_mipro(program, trainset, valset, config)
    elif config.optimizer == "copro":
        optimized_program, opt_results = _optimize_with_copro(program, trainset, config)
    elif config.optimizer == "bootstrap":
        optimized_program, opt_results = _optimize_with_bootstrap(program, trainset, config, random_search=False)
    elif config.optimizer == "bootstrap_random":
        optimized_program, opt_results = _optimize_with_bootstrap(program, trainset, config, random_search=True)
    else:
        raise ValueError(f"Unknown optimizer: {config.optimizer}")
    
    # Evaluate the optimized program
    eval_results = _evaluate_program(optimized_program, examples[split_idx:] if split_idx < len(examples) else examples[-1:])
    
    # Create comprehensive artifact
    artifact = {
        "timestamp": time.time(),
        "config": {
            "optimizer": config.optimizer,
            "model": config.model,
            "iters": config.iters,
            "include_unverified": config.include_unverified,
            "max_bootstrapped_demos": config.max_bootstrapped_demos,
            "max_labeled_demos": config.max_labeled_demos
        },
        "optimization_results": opt_results,
        "evaluation_results": eval_results,
        "dataset_info": {
            "total_examples": len(examples),
            "train_examples": len(trainset),
            "val_examples": len(valset)
        }
    }
    
    # Save artifact with proper DSPy program serialization
    print("🔧 DEBUG: Starting artifact save process...")
    artifact_dir = Path(config.artifact_dir)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = artifact_dir / "optimized_program.json"
    
    # Save the DSPy program using dspy.save()
    program_path = artifact_dir / "optimized_program_dspy"
    print(f"🔧 DEBUG: Attempting to save DSPy program to {program_path}")
    try:
        optimized_program.save(str(program_path), save_program=True)
        print(f"✅ DEBUG: Successfully saved DSPy program to {program_path}")
        logger.info(f"✅ Saved DSPy program to {program_path}")
    except Exception as e:
        print(f"❌ DEBUG: Failed to save DSPy program: {e}")
        logger.warning(f"⚠️ Failed to save DSPy program: {e}")
        # Fallback to old string representation
        artifact["program_state"] = str(optimized_program)
        program_path = None
    
    # Add program path to artifact metadata
    if program_path:
        print("✅ DEBUG: Adding program_path to artifact")
        artifact["program_path"] = str(program_path)
        artifact["program_info"] = {
            "summarizer_instruction": getattr(optimized_program.summarizer.predict, 'instructions', ''),
            "action_items_instruction": getattr(optimized_program.action_items.predict, 'instructions', ''),
            "model": config.model or "gpt-3.5-turbo"
        }
    else:
        print("❌ DEBUG: No program_path, using string fallback")
    
    print(f"💾 DEBUG: Saving artifact JSON to {artifact_path}")
    with artifact_path.open("w", encoding="utf-8") as fh:
        json.dump(artifact, fh, indent=2)
    
    print(f"✅ Optimization complete! Artifact saved to {artifact_path}")
    print(f"📈 Final composite F1 score: {eval_results['composite_f1']:.3f}")
    
    return {
        "success": True,
        "artifact_path": str(artifact_path),
        "composite_score": eval_results['composite_f1'],
        "summary_f1": eval_results['avg_summary_f1'],
        "action_f1": eval_results['avg_action_f1'],
        "optimization_time": opt_results.get('optimization_time', 0),
        "optimizer": config.optimizer
    }
