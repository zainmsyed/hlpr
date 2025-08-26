"""Simple evaluation metrics for meeting optimization.

These are lightweight heuristics; real optimization can later plug in ROUGE or semantic similarity.
"""
from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass

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
