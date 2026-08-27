# backend/app/services/nlp/entities.py
"""
Regex-based entity extraction for the two structured types that generic NER
handles well but that are just as reliably (and much more cheaply) caught by
pattern matching in legal text: money amounts and jurisdiction references.
Party/entity names are handled by defined_terms.py instead — see that
module's docstring for why that's the better signal in this domain.
"""
from __future__ import annotations

import re
from typing import List

from .schema import EntityMention

_MONEY_RE = re.compile(
    r"\$\s?[0-9][0-9,]*(?:\.[0-9]+)?|\b(?:USD|INR|EUR|GBP)\s?[0-9][0-9,]*(?:\.[0-9]+)?"
    r"|\b[0-9][0-9,]*(?:\.[0-9]+)?\s?(?:USD|dollars|rupees)\b",
    re.IGNORECASE,
)
_JURISDICTION_RE = re.compile(
    r"\b(?:State of|Commonwealth of|laws of)\s+([A-Z][a-zA-Z]+(?:\s[A-Z][a-zA-Z]+)?)"
)


def extract_entities(clause_text: str) -> List[EntityMention]:
    entities: List[EntityMention] = []

    for match in _MONEY_RE.finditer(clause_text):
        entities.append(EntityMention(text=match.group(0).strip(), type="money"))

    for match in _JURISDICTION_RE.finditer(clause_text):
        entities.append(EntityMention(text=match.group(1).strip(), type="jurisdiction"))

    return entities
