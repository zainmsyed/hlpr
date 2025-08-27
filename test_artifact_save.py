#!/usr/bin/env python3
"""Test script to debug DSPy artifact saving without running full optimization."""

import json
import logging
import time
from pathlib import Path

# Setup logging to see our messages
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def test_dspy_save():
    """Test DSPy program saving functionality."""
    try:
        import dspy
        from hlpr.dspy.signatures import ExtractActionItems, MeetingSummary
        
        print("🔧 Setting up DSPy...")
        
        # Initialize DSPy with a dummy model
        try:
            dspy.configure(lm=dspy.LM("gpt-3.5-turbo", api_key="test"))
        except Exception:
            print("⚠️ Using dummy LM configuration for testing")
        
        # Create a mock optimized program (same structure as in optimizer.py)
        class MockMeetingProgram(dspy.Module):
            def __init__(self):
                super().__init__()
                self.summarizer = dspy.ChainOfThought(MeetingSummary)
                self.action_items = dspy.ChainOfThought(ExtractActionItems)
                
                # Add some mock optimized instructions to simulate optimization
                if hasattr(self.summarizer.predict, 'instructions'):
                    self.summarizer.predict.instructions = "Mock optimized summary instruction"
                if hasattr(self.action_items.predict, 'instructions'):
                    self.action_items.predict.instructions = "Mock optimized action items instruction"

            def forward(self, transcript: str):
                s = self.summarizer(transcript=transcript).summary
                a = self.action_items(transcript=transcript).action_items
                return {"summary": s, "action_items": a}
        
        print("📦 Creating mock optimized program...")
        optimized_program = MockMeetingProgram()
        
        # Test the save functionality
        print("💾 Testing DSPy save functionality...")
        
        # Create test artifact directory
        artifact_dir = Path("test_artifacts/meeting")
        artifact_dir.mkdir(parents=True, exist_ok=True)
        
        # Try to save the DSPy program
        program_path = artifact_dir / "optimized_program_dspy"
        print(f"📁 Attempting to save to directory: {program_path}")
        
        try:
            optimized_program.save(str(program_path), save_program=True)
            logger.info(f"✅ Saved DSPy program to {program_path}")
            success = True
        except Exception as e:
            logger.warning(f"⚠️ Failed to save DSPy program: {e}")
            logger.warning(f"Exception type: {type(e)}")
            logger.warning(f"Exception args: {e.args}")
            success = False
        
        # Create mock artifact like the real optimizer does
        artifact = {
            "timestamp": time.time(),
            "config": {
                "optimizer": "test",
                "model": "gpt-3.5-turbo",
                "iters": 1,
                "include_unverified": False,
                "max_bootstrapped_demos": 4,
                "max_labeled_demos": 16
            },
            "optimization_results": {
                "optimizer": "test",
                "optimization_time": 0.0,
                "max_bootstrapped_demos": 4,
                "max_labeled_demos": 16,
                "trainset_size": 28,
                "valset_size": 7
            },
            "evaluation_results": {
                "avg_summary_f1": 0.5,
                "avg_action_f1": 0.3,
                "composite_f1": 0.4,
                "num_examples": 7
            },
            "dataset_info": {
                "total_examples": 35,
                "train_examples": 28,
                "val_examples": 7
            }
        }
        
        # Add program info if save was successful
        if success:
            artifact["program_path"] = str(program_path)
            artifact["program_info"] = {
                "summarizer_instruction": getattr(optimized_program.summarizer.predict, 'instructions', ''),
                "action_items_instruction": getattr(optimized_program.action_items.predict, 'instructions', ''),
                "model": "gpt-3.5-turbo"
            }
            print("✅ Added program_path and program_info to artifact")
        else:
            # Fallback to old string representation
            artifact["program_state"] = str(optimized_program)
            print("⚠️ Added program_state string fallback to artifact")
        
        # Save the artifact JSON
        artifact_path = artifact_dir / "optimized_program.json"
        with artifact_path.open("w", encoding="utf-8") as fh:
            json.dump(artifact, fh, indent=2)
        
        print(f"💾 Saved artifact JSON to {artifact_path}")
        
        # Show results
        print("\n📊 Results:")
        print(f"  DSPy save successful: {success}")
        if success:
            print(f"  Program directory exists: {program_path.exists()}")
            if program_path.exists():
                contents = list(program_path.iterdir())
                print(f"  Directory contents: {[f.name for f in contents]}")
        
        print(f"  Artifact JSON exists: {artifact_path.exists()}")
        
        # Show artifact content
        print("\n📄 Artifact content preview:")
        if artifact_path.exists():
            with open(artifact_path) as f:
                content = f.read()
                if len(content) > 500:
                    print(content[:500] + "...")
                else:
                    print(content)
        
        return success
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🧪 Testing DSPy artifact saving...")
    success = test_dspy_save()
    print(f"\n🎯 Test {'PASSED' if success else 'FAILED'}")