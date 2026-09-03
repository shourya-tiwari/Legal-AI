# backend/app/services/nlp/entities.py
"""
Entity extraction. Two layers:

  1. Regex (Class A, always on) -- money amounts and jurisdiction references,
     the two structured types pattern matching catches cheaply and reliably in
     legal text. This is the floor: it runs with no model installed.
  2. GLiNER zero-shot NER (Class B, Phase 6) via the Model Router `ner_extract`
     task -- adds parties/organizations/people, dates, durations, and statute
     citations when the optional `gliner` extra is present. Fail-soft: any
     router error falls back to regex-only.

Party/entity NAMES are still primarily handled by defined_terms.py (contracts
name their key entities as defined terms); GLiNER complements that for parties
mentioned without a formal definition.
"""
from __future__ import annotations

import logging
import re
from functools import lru_cache
from typing import List

from app.config import get_settings
from app.services.model_router import ModelRouterError, ner_extract

from .schema import EntityMention

logger = logging.getLogger("legalai.nlp.entities")

_MONEY_RE = re.compile(
    r"\$\s?[0-9][0-9,]*(?:\.[0-9]+)?|\b(?:USD|INR|EUR|GBP)\s?[0-9][0-9,]*(?:\.[0-9]+)?"
    r"|\b[0-9][0-9,]*(?:\.[0-9]+)?\s?(?:USD|dollars|rupees)\b",
    re.IGNORECASE,
)
_JURISDICTION_RE = re.compile(
    r"\b(?:State of|Commonwealth of|laws of)\s+([A-Z][a-zA-Z]+(?:\s[A-Z][a-zA-Z]+)?)"
)

# GLiNER label -> EntityMention.type
_NER_TYPE_MAP = {
    "party": "party",
    "organization": "party",
    "person": "party",
    "monetary amount": "money",
    "date": "date",
    "duration": "duration",
    "governing law jurisdiction": "jurisdiction",
    "statute citation": "statute",
}


@lru_cache(maxsize=1)
def _ner_available() -> bool:
    """One cheap check per process: is the GLiNER provider usable?"""
    try:
        from app.services.model_router.registry import get_provider

        p = get_provider("local-ner")
        return bool(p and p.is_available())
    except Exception:  # pragma: no cover
        return False


def _regex_entities(clause_text: str) -> List[EntityMention]:
    out: List[EntityMention] = []
    for m in _MONEY_RE.finditer(clause_text):
        out.append(EntityMention(text=m.group(0).strip(), type="money"))
    for m in _JURISDICTION_RE.finditer(clause_text):
        out.append(EntityMention(text=m.group(1).strip(), type="jurisdiction"))
    return out


def _ner_entities(clause_text: str) -> List[EntityMention]:
    labels = get_settings().NER_LABELS
    try:
        result = ner_extract(clause_text, labels)
    except ModelRouterError as e:
        logger.debug("NER unavailable for this clause (%s); regex only.", e)
        return []
    out: List[EntityMention] = []
    for e in result.entities:
        mapped = _NER_TYPE_MAP.get(e["type"])
        if mapped:
            out.append(EntityMention(text=e["text"].strip(), type=mapped))
    return out


def _dedup(entities: List[EntityMention]) -> List[EntityMention]:
    seen: set = set()
    out: List[EntityMention] = []
    for e in entities:
        key = (e.type, e.text.lower())
        if key not in seen:
            seen.add(key)
            out.append(e)
    return out


def extract_entities(clause_text: str) -> List[EntityMention]:
    entities = _regex_entities(clause_text)
    if get_settings().NER_ENABLED and _ner_available():
        entities += _ner_entities(clause_text)
    return _dedup(entities)
