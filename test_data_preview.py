#!/usr/bin/env python3
"""Quick test to show what training data will be used for optimization."""

from src.hlpr.dspy.dataset import load_meeting_examples

def main():
    # Default CLI settings: include_unverified=False
    print("=== VERIFIED EXAMPLES ONLY (default CLI behavior) ===")
    verified_examples = load_meeting_examples(
        "documents/training-data/meetings.txt", 
        include_unverified=False
    )
    print(f"Total verified examples: {len(verified_examples)}")
    
    print("\nFirst 3 verified examples:")
    for i, ex in enumerate(verified_examples[:3]):
        print(f"\n{i+1}. ID: {ex.id}")
        print(f"   Transcript: {ex.transcript[:100]}...")
        print(f"   Gold Summary: {ex.gold_summary[:100]}...")
        print(f"   Action Items: {ex.action_items}")
        print(f"   Strategy: {ex.synthetic_strategy}")
    
    print("\n" + "="*60)
    print("=== ALL EXAMPLES (with --include-unverified) ===")
    all_examples = load_meeting_examples(
        "documents/training-data/meetings.txt", 
        include_unverified=True
    )
    print(f"Total examples (verified + unverified): {len(all_examples)}")
    
    # Show some unverified examples
    unverified = [ex for ex in all_examples if not ex.verified]
    print(f"Unverified examples: {len(unverified)}")
    print("\nFirst unverified example:")
    if unverified:
        ex = unverified[0]
        print(f"   ID: {ex.id}")
        print(f"   Transcript: {ex.transcript[:100]}...")
        print(f"   Gold Summary: {ex.gold_summary[:100]}...")
        print(f"   Strategy: {ex.synthetic_strategy} (contains issues)")

if __name__ == "__main__":
    main()
