# backend/app/services/nlp/defined_terms.py
"""
Defined-term extraction: contracts almost always introduce their key
entities (parties, key dates, key concepts) via an explicit defined-term
pattern — `ABC Corporation ("Company")` or `"Effective Date" means ...` —
before using the shorthand throughout the rest of the document. Extracting
these is a regex problem, not an NER problem, and it's also this project's
answer to "who are the parties" (docs/v2/NLP.md's NER stage): the parties are
almost always among the defined terms, which is a more reliable signal for
this domain than generic person/org NER would be.
"""
from __future__ import annotations

import re
from typing import Dict, List

# ABC Corporation ("Company") / the Landlord ("Landlord")
_PAREN_DEFINED_TERM_RE = re.compile(
    r'\(\s*(?:the\s+)?["“]([A-Z][A-Za-z0-9 &,\.\'\-]{1,50})["”]\s*\)'
)
# "Effective Date" means January 1, 2025 / "Company" shall mean ABC Corp
_MEANS_DEFINED_TERM_RE = re.compile(
    r'["“]([A-Z][A-Za-z0-9 &,\.\'\-]{1,50})["”]\s+(?:means|shall mean|refers to)\b',
    re.IGNORECASE,
)


def extract_defined_terms(full_text: str) -> Dict[str, str]:
    """Returns {term: surrounding context}, first definition wins per term."""
    terms: Dict[str, str] = {}

    for match in _PAREN_DEFINED_TERM_RE.finditer(full_text or ""):
        term = match.group(1).strip()
        context_start = max(0, match.start() - 100)
        terms.setdefault(term, full_text[context_start:match.end()].strip())

    for match in _MEANS_DEFINED_TERM_RE.finditer(full_text or ""):
        term = match.group(1).strip()
        context_end = min(len(full_text), match.end() + 150)
        terms.setdefault(term, full_text[match.start():context_end].strip())

    return terms


def find_term_usages(clause_text: str, defined_terms: Dict[str, str]) -> List[str]:
    used = []
    for term in defined_terms:
        if re.search(r"\b" + re.escape(term) + r"\b", clause_text):
            used.append(term)
    return used
