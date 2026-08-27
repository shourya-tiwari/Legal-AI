# backend/app/services/nlp/clause_classifier.py
"""
Clause-type classification: a keyword-taxonomy rule base (Tier 0, same style
as V1's services/risk_radar/rules.py), with optional Gemini escalation for
clauses no keyword set matches confidently. The taxonomy mirrors the common
clause categories CUAD (docs/v2/AI_STACK.md's eval corpus) labels, so this
rule-based classifier's output is directly comparable to CUAD ground truth
once that dataset is wired into the eval harness.
"""
from __future__ import annotations

from typing import Dict, List, Tuple

from ..model_router import generate_content

CLAUSE_TYPE_KEYWORDS: Dict[str, List[str]] = {
    "indemnification": ["indemnify", "indemnification", "hold harmless"],
    "limitation_of_liability": ["limitation of liability", "liability shall not exceed", "in no event shall"],
    "termination": ["terminate", "termination", "notice of termination"],
    "confidentiality": ["confidential", "non-disclosure", "proprietary information"],
    "assignment": ["assign", "assignment", "successors and assigns"],
    "governing_law": ["governing law", "governed by the laws of", "governed by", "construed in accordance with", "jurisdiction"],
    "dispute_resolution": ["arbitration", "dispute resolution", "mediation"],
    "force_majeure": ["force majeure", "act of god"],
    "ip_ownership": ["intellectual property", "work product", "ownership of inventions"],
    "payment_terms": ["payment", "invoice", "fees shall be paid", "due within"],
    "renewal": ["renew", "renewal", "automatically renews"],
    "insurance": ["insurance", "coverage requirements"],
}

_ESCALATION_PROMPT = """Classify this contract clause into exactly one category from this list,
or "other" if none fit: {categories}.

Return only the category name, nothing else.

Clause: "{clause}"
"""


def classify_clause_type_rule_based(clause_text: str) -> str | None:
    normalized = clause_text.lower()
    best_type, best_hits = None, 0

    for clause_type, keywords in CLAUSE_TYPE_KEYWORDS.items():
        hits = sum(1 for kw in keywords if kw in normalized)
        if hits > best_hits:
            best_type, best_hits = clause_type, hits

    return best_type


def classify_clause_type(clause_text: str, use_ai_escalation: bool = False) -> Tuple[str, str]:
    rule_result = classify_clause_type_rule_based(clause_text)
    if rule_result:
        return rule_result, "rule"
    if not use_ai_escalation:
        return "other", "rule"

    try:
        prompt = _ESCALATION_PROMPT.format(categories=", ".join(CLAUSE_TYPE_KEYWORDS.keys()), clause=clause_text)
        raw = generate_content(prompt, temperature=0.0).strip().lower().replace(" ", "_").strip(".")
        if raw in CLAUSE_TYPE_KEYWORDS:
            return raw, "ai"
        return "other", "ai"
    except Exception:
        return "other", "rule"
