# backend/app/eval/metrics.py
"""
Pure-stdlib scoring metrics for the eval harness (app/eval/tasks.py,
cutover_gate.py). No sklearn / numpy -- these run in the fast lane and in CI.

 - exact_match / token_f1        : free-text answers
 - squad_f1                      : CUAD-style QA (max over gold answers; the
                                   empty-gold "not present" case scores 1.0
                                   only when the prediction is also empty)
 - accuracy / macro_f1           : classification (NLI labels, clause types)
"""
from __future__ import annotations

import re
import string
from collections import Counter
from typing import Iterable, List, Sequence

_ARTICLES_RE = re.compile(r"\b(a|an|the)\b", re.IGNORECASE)
_PUNCT_TABLE = str.maketrans("", "", string.punctuation)


def normalize_text(s: str) -> str:
    s = (s or "").lower().translate(_PUNCT_TABLE)
    s = _ARTICLES_RE.sub(" ", s)
    return " ".join(s.split())


def exact_match(pred: str, gold: str) -> float:
    return 1.0 if normalize_text(pred) == normalize_text(gold) else 0.0


def token_f1(pred: str, gold: str) -> float:
    pt = normalize_text(pred).split()
    gt = normalize_text(gold).split()
    if not pt and not gt:
        return 1.0
    if not pt or not gt:
        return 0.0
    common = Counter(pt) & Counter(gt)
    overlap = sum(common.values())
    if overlap == 0:
        return 0.0
    precision = overlap / len(pt)
    recall = overlap / len(gt)
    return 2 * precision * recall / (precision + recall)


def squad_f1(pred: str, golds: Sequence[str]) -> float:
    """Max token-F1 over the acceptable gold answers. `golds` empty means
    'the contract does not contain this' -- rewarded only if the prediction
    is also empty / a negative."""
    golds = [g for g in (golds or []) if g and g.strip()]
    if not golds:
        p = normalize_text(pred)
        return 1.0 if (not p or p in {"none", "not present", "n a", "no", "not found"}) else 0.0
    return max(token_f1(pred, g) for g in golds)


def accuracy(preds: Sequence[str], golds: Sequence[str]) -> float:
    if not golds:
        return 0.0
    return sum(1 for p, g in zip(preds, golds) if p == g) / len(golds)


def macro_f1(preds: Sequence[str], golds: Sequence[str], labels: Iterable[str] | None = None) -> float:
    labels = list(labels) if labels is not None else sorted(set(golds) | set(preds))
    if not labels:
        return 0.0
    f1s: List[float] = []
    for label in labels:
        tp = sum(1 for p, g in zip(preds, golds) if p == label and g == label)
        fp = sum(1 for p, g in zip(preds, golds) if p == label and g != label)
        fn = sum(1 for p, g in zip(preds, golds) if p != label and g == label)
        if tp == 0:
            f1s.append(0.0)
            continue
        precision = tp / (tp + fp)
        recall = tp / (tp + fn)
        f1s.append(2 * precision * recall / (precision + recall))
    return sum(f1s) / len(f1s)
