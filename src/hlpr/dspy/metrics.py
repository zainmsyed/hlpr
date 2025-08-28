"""Simple evaluation metrics for meeting optimization.

These are lightweight heuristics; real optimization can later plug in ROUGE or semantic similarity.
"""
from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from difflib import SequenceMatcher

TOKEN_RE = re.compile(r"\w+")


def _tokenize(text: str) -> list[str]:
    return [t.lower() for t in TOKEN_RE.findall(text)]


@dataclass(slots=True)
class PRF:
    precision: float
    recall: float
    f1: float


def prf_from_counts(tp: int, pred_total: int, gold_total: int) -> PRF:
    precision = tp / pred_total if pred_total else 0.0
    recall = tp / gold_total if gold_total else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if precision + recall else 0.0
    return PRF(precision, recall, f1)


def summary_token_overlap(pred: str, gold: str) -> PRF:
    p_tokens = _tokenize(pred)
    g_tokens = _tokenize(gold)
    pc = Counter(p_tokens)
    gc = Counter(g_tokens)
    tp = sum(min(pc[w], gc[w]) for w in pc.keys() & gc.keys())
    return prf_from_counts(tp, sum(pc.values()), sum(gc.values()))


def _normalize_string(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower())


def list_exact_match(pr: Iterable[str], gold: Iterable[str]) -> PRF:
    p_norm = [_normalize_string(x) for x in pr]
    g_norm = [_normalize_string(x) for x in gold]
    p_counts = Counter(p_norm)
    g_counts = Counter(g_norm)
    tp = sum(min(p_counts[k], g_counts[k]) for k in p_counts.keys() & g_counts.keys())
    return prf_from_counts(tp, sum(p_counts.values()), sum(g_counts.values()))


def fuzzy_list_match(pred_items: list[str], gold_items: list[str], threshold: float = 0.6) -> PRF:
    """Fuzzy matching for action items with partial credit using sequence similarity."""
    if not gold_items:
        return PRF(precision=0.0, recall=0.0, f1=0.0) if pred_items else PRF(precision=1.0, recall=1.0, f1=1.0)
    
    matched_gold = set()
    tp = 0
    
    for pred in pred_items:
        pred_norm = _normalize_string(pred)
        best_match = None
        best_score = 0.0
        
        for i, gold in enumerate(gold_items):
            if i in matched_gold:
                continue
            
            gold_norm = _normalize_string(gold)
            # Use sequence matcher for fuzzy matching
            score = SequenceMatcher(None, pred_norm, gold_norm).ratio()
            
            if score > best_score and score >= threshold:
                best_match = i
                best_score = score
        
        if best_match is not None:
            matched_gold.add(best_match)
            tp += 1
    
    precision = tp / len(pred_items) if pred_items else 1.0
    recall = tp / len(gold_items)
    f1 = (2 * precision * recall / (precision + recall)) if precision + recall else 0.0
    
    return PRF(precision=precision, recall=recall, f1=f1)


def semantic_similarity_score(pred: str, gold: str) -> float:
    """Calculate semantic similarity using sentence transformers (with fallback)."""
    try:
        from sentence_transformers import SentenceTransformer
        from sklearn.metrics.pairwise import cosine_similarity
        
        # Use a lightweight model
        model = SentenceTransformer('all-MiniLM-L6-v2')
        pred_embedding = model.encode([pred])
        gold_embedding = model.encode([gold])
        
        similarity = cosine_similarity(pred_embedding, gold_embedding)[0][0]
        return float(similarity)
        
    except ImportError:
        # Fallback to token overlap if sentence-transformers not available
        token_score = summary_token_overlap(pred, gold).f1
        # Boost the score slightly to account for semantic understanding
        return min(token_score * 1.2, 1.0)
    except Exception:
        # Final fallback to token overlap
        return summary_token_overlap(pred, gold).f1


def summary_quality_score(summary: str, original_length: int = 0) -> float:
    """Assess summary quality based on length, coherence, and structure."""
    if not summary.strip():
        return 0.0
    
    score = 0.0
    
    # Length appropriateness (ideal: 20-30% of original)
    if original_length > 0:
        length_ratio = len(summary.split()) / original_length
        if 0.15 <= length_ratio <= 0.4:
            score += 0.3
        elif 0.1 <= length_ratio <= 0.5:
            score += 0.2
    
    # Sentence structure (has multiple sentences)
    sentences = re.split(r'[.!?]+', summary)
    sentences = [s.strip() for s in sentences if s.strip()]
    if len(sentences) >= 2:
        score += 0.2
    
    # Completeness (ends with punctuation)
    if summary.strip().endswith(('.', '!', '?')):
        score += 0.1
    
    # No obvious artifacts (no repeated phrases)
    words = summary.lower().split()
    if len(words) > 10:
        # Check for excessive repetition
        word_counts = Counter(words)
        max_repetition = max(word_counts.values())
        if max_repetition <= len(words) * 0.1:  # No word repeated more than 10% of total
            score += 0.2
    
    # Basic coherence (not just keywords)
    avg_word_length = sum(len(word) for word in words) / len(words) if words else 0
    if avg_word_length >= 4:  # Average word length suggests real sentences
        score += 0.2
    
    return min(score, 1.0)
