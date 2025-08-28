"""Advanced MIPRO optimization pipeline for meeting processing using DSPy.

This implements multiple optimization strategies including MIPROv2 and BootstrapFewShot
with comprehensive evaluation and artifact management.
"""
from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import dspy
from dspy.teleprompt import BootstrapFewShot, MIPROv2

from hlpr.core.errors import DatasetLoadError, ModelConfigurationError, OptimizationError
from hlpr.core.optimization import OptimizationConfig

from .dataset import load_meeting_examples
from .metrics import (
    fuzzy_list_match,
    list_exact_match,
    semantic_similarity_score,
    summary_quality_score,
    summary_token_overlap,
)
from .programs import MeetingProgram

logger = logging.getLogger(__name__)


class MeetingEvaluator:
    """Centralized evaluation for meeting optimization."""
    
    def __init__(self, metrics: list[str] | None = None, use_enhanced: bool = True):
        self.metrics = metrics or ["summary_f1", "action_f1"]
        self.use_enhanced = use_enhanced
    
    def evaluate(self, program: Any, examples: list[Any]) -> dict[str, float]:
        """Evaluate program on examples with all configured metrics."""
        results: dict[str, list[float]] = {}
        
        for example in examples:
            pred = program(transcript=example.transcript)
            
            # Calculate individual metrics
            if "summary_f1" in self.metrics:
                if self.use_enhanced and "semantic" in self.metrics:
                    # Use semantic similarity for summary
                    summary_score = semantic_similarity_score(pred["summary"], example.gold_summary)
                else:
                    # Use token overlap
                    summary_score = summary_token_overlap(pred["summary"], example.gold_summary).f1
                results.setdefault("summary_scores", []).append(summary_score)
            
            if "action_f1" in self.metrics:
                if self.use_enhanced:
                    # Use fuzzy matching for action items
                    action_score = fuzzy_list_match(pred["action_items"], example.action_items).f1
                else:
                    # Use exact matching
                    action_score = list_exact_match(pred["action_items"], example.action_items).f1
                results.setdefault("action_scores", []).append(action_score)
            
            if "summary_quality" in self.metrics and self.use_enhanced:
                # Calculate summary quality score
                quality_score = summary_quality_score(pred["summary"], len(example.transcript.split()))
                results.setdefault("quality_scores", []).append(quality_score)
        
        # Aggregate results
        eval_results = {}
        if "summary_scores" in results:
            eval_results["avg_summary_f1"] = sum(results["summary_scores"]) / len(results["summary_scores"])
        if "action_scores" in results:
            eval_results["avg_action_f1"] = sum(results["action_scores"]) / len(results["action_scores"])
        if "quality_scores" in results:
            eval_results["avg_quality_score"] = sum(results["quality_scores"]) / len(results["quality_scores"])
        
        # Composite score
        eval_results["composite_f1"] = self.composite_score(eval_results)
        eval_results["num_examples"] = len(examples)
        
        return eval_results
    
    def composite_score(self, results: dict[str, float]) -> float:
        """Calculate composite score from individual metrics."""
        scores = []
        weights = []
        
        if "avg_summary_f1" in results:
            scores.append(results["avg_summary_f1"])
            weights.append(0.4)  # 40% weight for summary
        
        if "avg_action_f1" in results:
            scores.append(results["avg_action_f1"])
            weights.append(0.4)  # 40% weight for action items
        
        if "avg_quality_score" in results:
            scores.append(results["avg_quality_score"])
            weights.append(0.2)  # 20% weight for quality
        
        if not scores:
            return 0.0
        
        # Weighted average
        total_weight = sum(weights)
        if total_weight == 0:
            return sum(scores) / len(scores)
        
        return sum(score * weight for score, weight in zip(scores, weights, strict=False)) / total_weight
    
    def create_metric_function(self) -> Callable[..., float]:
        """Create a metric function for DSPy optimizers."""
        def meeting_metric(gold: Any, pred: Any, trace: Any = None) -> float:
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
            
            # Calculate metrics with enhanced options
            if self.use_enhanced:
                # Use semantic similarity for summary if available
                try:
                    summary_score = semantic_similarity_score(pred_summary, gold_summary)
                except Exception:
                    summary_score = summary_token_overlap(pred_summary, gold_summary).f1
                
                # Use fuzzy matching for action items
                action_score = fuzzy_list_match(pred_actions, gold_actions).f1
            else:
                # Fallback to basic metrics
                summary_score = summary_token_overlap(pred_summary, gold_summary).f1
                action_score = list_exact_match(pred_actions, gold_actions).f1
            
            # Composite score
            return (summary_score + action_score) / 2.0
        
        return meeting_metric


def configure_model(model: str | None = None) -> None:
    """Configure DSPy model with environment-aware defaults."""
    model = model or get_default_model()
    
    try:
        if model.startswith("ollama/"):
            configure_ollama_model(model)
        else:
            configure_openai_model(model)
    except Exception as e:
        logger.error(f"Model configuration failed: {e}")
        raise ModelConfigurationError(f"Failed to configure model {model}: {e}") from e

def get_default_model() -> str:
    """Get default model based on environment."""
    # Use environment detection from CLI plan
    if is_ollama_available():
        return "ollama/gemma3"
    return "gpt-3.5-turbo"

def configure_ollama_model(model: str) -> None:
    """Configure DSPy for Ollama models."""
    model_name = model.split("/")[-1]
    api_base = "http://localhost:11434"  # Simplified - no Docker detection
    
    lm = dspy.LM(model=f"ollama/{model_name}", api_base=api_base)
    dspy.configure(lm=lm)
    logger.info(f"Configured DSPy with Ollama model: {model_name} at {api_base}")

def configure_openai_model(model: str) -> None:
    """Configure DSPy for OpenAI-compatible models."""
    lm = dspy.LM(model=model)
    dspy.configure(lm=lm)
    logger.info(f"Configured DSPy with model: {model}")

def is_ollama_available() -> bool:
    """Check if Ollama is available (simplified check)."""
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        return bool(response.status_code == 200)
    except Exception:
        return False


def _convert_to_dspy_examples(meeting_examples: list[Any]) -> list[dspy.Example]:
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


def _optimize_with_mipro(program: MeetingProgram, trainset: list[dspy.Example], valset: list[dspy.Example], config: OptimizationConfig) -> tuple[Any, dict[str, Any]]:
    """Optimize using MIPROv2."""
    logger.info("Starting MIPROv2 optimization")
    
    # Use centralized evaluator
    evaluator = MeetingEvaluator()
    
    # Initialize MIPROv2 optimizer
    optimizer = MIPROv2(
        metric=evaluator.create_metric_function(),
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


def _optimize_with_bootstrap(program: MeetingProgram, trainset: list[dspy.Example], config: OptimizationConfig) -> tuple[Any, dict[str, Any]]:
    """Optimize using BootstrapFewShot."""
    logger.info("Starting BootstrapFewShot optimization")
    
    # Use centralized evaluator
    evaluator = MeetingEvaluator()
    
    # Initialize BootstrapFewShot optimizer
    optimizer = BootstrapFewShot(
        metric=evaluator.create_metric_function(),
        max_bootstrapped_demos=config.max_bootstrapped_demos,
        max_labeled_demos=config.max_labeled_demos
    )
    
    # Run optimization
    start_time = time.time()
    optimized_program = optimizer.compile(program, trainset=trainset)
    optimization_time = time.time() - start_time
    
    results = {
        "optimizer": "bootstrap",
        "optimization_time": optimization_time,
        "max_bootstrapped_demos": config.max_bootstrapped_demos,
        "max_labeled_demos": config.max_labeled_demos,
        "trainset_size": len(trainset)
    }
    
    return optimized_program, results


def _save_optimization_artifact(program: Any, metadata: dict[str, Any], artifact_dir: Path) -> str:
    """Save optimization results to artifact directory.
    
    Args:
        program: The optimized DSPy program
        metadata: Metadata dictionary with config, results, etc.
        artifact_dir: Directory to save artifacts in
        
    Returns:
        Path to the saved artifact JSON file
    """
    artifact_dir.mkdir(parents=True, exist_ok=True)
    
    # Save DSPy program using native format
    program_path = artifact_dir / "optimized_program"
    try:
        program.save(str(program_path), save_program=True)
        logger.info(f"Saved DSPy program to {program_path}")
    except Exception as e:
        logger.warning(f"Failed to save DSPy program: {e}")
        # Continue with JSON-only artifact
    
    # Save metadata as JSON
    metadata_path = artifact_dir / "metadata.json"
    with metadata_path.open("w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    
    logger.info(f"Saved optimization metadata to {metadata_path}")
    return str(metadata_path)


def optimize(config: OptimizationConfig) -> dict[str, Any]:
    """Run the complete MIPRO optimization pipeline."""
    logger.info(f"Starting optimization with {config.optimizer} strategy")
    
    # Initialize model
    configure_model(config.model)
    
    # Load examples
    try:
        examples = load_meeting_examples(
            config.data_path, include_unverified=config.include_unverified
        )
        if not examples:
            raise DatasetLoadError(config.data_path)
    except Exception as e:
        if isinstance(e, DatasetLoadError):
            raise
        raise DatasetLoadError(config.data_path, e) from e
    
    logger.info(f"Loaded {len(examples)} examples for optimization")
    
    # Convert to DSPy format
    dspy_examples = _convert_to_dspy_examples(examples)
    
    # Split into train/validation sets using config parameter
    split_idx = int(config.train_split * len(dspy_examples))
    trainset = dspy_examples[:split_idx]
    valset = dspy_examples[split_idx:] if split_idx < len(dspy_examples) else dspy_examples[-1:]
    
    logger.info(f"Train set: {len(trainset)} examples, Validation set: {len(valset)} examples")
    
    # Initialize program
    program = MeetingProgram()
    
    # Run optimization based on strategy
    if config.optimizer == "mipro":
        optimized_program, opt_results = _optimize_with_mipro(program, trainset, valset, config)
    elif config.optimizer == "bootstrap":
        optimized_program, opt_results = _optimize_with_bootstrap(program, trainset, config)
    else:
        raise OptimizationError(
            f"Unknown optimizer: {config.optimizer}. Supported: mipro, bootstrap",
            suggestions=["Use 'mipro' for advanced optimization or 'bootstrap' for quick optimization"],
            context={"available_optimizers": ["mipro", "bootstrap"], "requested_optimizer": config.optimizer}
        )
    
    # Evaluate the optimized program
    evaluator = MeetingEvaluator()
    eval_results = evaluator.evaluate(optimized_program, examples[split_idx:] if split_idx < len(examples) else examples[-1:])
    
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
    
    # Save artifact using simplified approach
    artifact_dir = Path(config.artifact_dir)
    artifact_path = _save_optimization_artifact(optimized_program, artifact, artifact_dir)
    
    logger.info(f"Optimization complete! Artifact saved to {artifact_path}")
    # User-facing output for final results
    print(f"📈 Final composite F1 score: {eval_results['composite_f1']:.3f}")
    print(f"💾 Artifact saved to: {artifact_path}")
    print(f"⏱️  Optimization time: {opt_results.get('optimization_time', 0):.1f}s")
    
    return {
        "success": True,
        "artifact_path": artifact_path,
        "composite_score": eval_results['composite_f1'],
        "summary_f1": eval_results['avg_summary_f1'],
        "action_f1": eval_results['avg_action_f1'],
        "optimization_time": opt_results.get('optimization_time', 0),
        "optimizer": config.optimizer
    }
