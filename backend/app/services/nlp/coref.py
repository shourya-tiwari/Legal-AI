# backend/app/services/nlp/coref.py
"""
NOT real coreference resolution. This is a narrow heuristic: when a clause
uses a generic role word ("the Company", "it", "the Landlord") without an
explicit defined term of its own, list the most recently-seen defined terms
in the document as *candidates* the pronoun/role word probably refers to.

docs/v2/NLP.md's actual plan for this stage is a real coreference model
(fastcoref, with an LLM fallback for long-range references) — deferred here
because it's a meaningfully-sized model better run once GPU access exists
(see docs/v2/ROADMAP.md's GPU upgrade phase). This heuristic exists so the
pipeline has *something* here now, not nothing, and so its output shape
(`pronoun_candidates: List[str]`) is already in place for a real resolver to
fill in later without a schema change.
"""
from __future__ import annotations

import re
from typing import List

_GENERIC_ROLE_RE = re.compile(
    r"\b(it|its|they|their|the Company|the Tenant|the Landlord|the Employer|"
    r"the Employee|the Vendor|the Client|the Party|the Parties)\b",
    re.IGNORECASE,
)

MAX_CANDIDATES = 2


def resolve_pronoun_candidates(clause_text: str, defined_terms_used: List[str], preceding_terms: List[str]) -> List[str]:
    """`preceding_terms` should be defined terms already seen earlier in the
    document, most-recent last. Returns [] if the clause already names its
    own defined term (no ambiguity to flag)."""
    if defined_terms_used or not _GENERIC_ROLE_RE.search(clause_text):
        return []
    return list(reversed(preceding_terms[-MAX_CANDIDATES:]))
