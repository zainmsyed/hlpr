"""Unified configuration system for optimization tasks.

Provides a centralized configuration management system with presets
for different optimization scenarios.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


@dataclass
class OptimizationConfig:
    """Unified configuration for all optimization tasks."""
    
    # Core settings
    optimizer: Literal["mipro", "bootstrap"] = "mipro"
    model: str | None = None
    iters: int = 5  # Reserved for future optimization iteration control
    
    # Data settings  
    data_path: str = "documents/training-data/meetings.txt"
    include_unverified: bool = False
    train_split: float = 0.8
    
    # Advanced settings
    max_bootstrapped_demos: int = 4
    max_labeled_demos: int = 16
    
    # Output settings
    artifact_dir: str = "artifacts/meeting"
    
    @classmethod
    def from_preset(cls, preset: str) -> OptimizationConfig:
        """Load configuration from preset."""
        presets = {
            "quick": cls(
                optimizer="bootstrap", 
                iters=1, 
                model="ollama/gemma3",
                max_bootstrapped_demos=2,
                max_labeled_demos=8
            ),
            "development": cls(
                optimizer="bootstrap", 
                iters=2, 
                include_unverified=True,
                max_bootstrapped_demos=3,
                max_labeled_demos=12
            ),
            "production": cls(
                optimizer="mipro", 
                iters=10, 
                model="gpt-4",
                max_bootstrapped_demos=8,
                max_labeled_demos=32
            ),
            "thorough": cls(
                optimizer="mipro",
                iters=15,
                model="gpt-4",
                max_bootstrapped_demos=12,
                max_labeled_demos=48
            )
        }
        
        if preset not in presets:
            raise ValueError(f"Unknown preset: {preset}. Available: {list(presets.keys())}")
            
        return presets[preset]
    
    @classmethod
    def list_presets(cls) -> dict[str, str]:
        """List available presets with descriptions."""
        return {
            "quick": "Fast optimization with BootstrapFewShot (1 iteration, local model)",
            "development": "Development optimization with noisy data (2 iterations)",
            "production": "Production-ready optimization with MIPRO (10 iterations, GPT-4)",
            "thorough": "Comprehensive optimization with MIPRO (15 iterations, GPT-4)"
        }
    
    def to_dict(self) -> dict[str, Any]:
        """Convert config to dictionary for serialization."""
        return {
            "optimizer": self.optimizer,
            "model": self.model,
            "iters": self.iters,
            "data_path": self.data_path,
            "include_unverified": self.include_unverified,
            "train_split": self.train_split,
            "max_bootstrapped_demos": self.max_bootstrapped_demos,
            "max_labeled_demos": self.max_labeled_demos,
            "artifact_dir": self.artifact_dir
        }