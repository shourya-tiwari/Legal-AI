# backend/app/services/nlp/ambiguity.py
"""Vague/ambiguous standard-of-performance detection: extends V1's risk
keyword list (services/risk_radar/rules.py) into a dedicated ambiguity
signal, since "this term is vague" and "this term is risky" are related but
distinct judgments (a clause can be a clear, unambiguous, and still risky
obligation)."""
from __future__ import annotations

from typing import Dict, List

from .schema import AmbiguityFlag

VAGUE_TERMS: Dict[str, str] = {
    "best efforts": "Vague obligation, unclear standard of performance",
    "reasonable efforts": "Ambiguous level of obligation, may differ by context",
    "commercially reasonable": "Subjective and open to interpretation",
    "material adverse change": "Broad clause, often undefined, triggering major rights",
    "sole discretion": "Gives one party complete decision-making power",
    "good faith": "Ambiguous standard, hard to enforce",
    "as soon as practicable": "No fixed deadline, subjective timing",
    "from time to time": "Undefined frequency",
    "reasonable time": "No fixed deadline, subjective timing",
    "substantially similar": "No objective threshold for comparison",
}


def detect_ambiguity(clause_text: str) -> List[AmbiguityFlag]:
    normalized = clause_text.lower()
    return [
        AmbiguityFlag(term=term, explanation=explanation)
        for term, explanation in VAGUE_TERMS.items()
        if term in normalized
    ]
