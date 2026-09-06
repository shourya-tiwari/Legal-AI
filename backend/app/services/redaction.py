# backend/app/services/redaction.py
"""
PII/PHI redaction gate (docs/v2/ARCHITECTURE.md Security architecture, item 3):
"Before any text is sent to a Class C provider, a local NER-based redaction
pass flags/masks personal identifiers not required for the task."

Same two-layer pattern as app/services/nlp/entities.py:
  1. Regex (Class A, always on) -- SSN, credit card, email, phone. Structured
     PII a deterministic pattern catches reliably with no model installed.
     This is the floor: the security property holds even air-gapped.
  2. GLiNER zero-shot NER (Class B, Phase 6) via the Model Router `ner_extract`
     task -- adds person names and physical addresses, which no regex can
     reliably catch. Fail-soft: any router error and the regex floor alone
     still applies.

Called from the Model Router (router.py) immediately before a Class C
provider is dispatched -- self-hosted (Class B) calls never pass through
this, so an on-prem/air-gapped deployment sees no behavior change at all.
Per-org configurable "never send to third party" categories are a documented
follow-up (needs an org-settings model that doesn't exist yet); this gate
applies one fixed, global category set.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from app.config import get_settings
from app.services.model_router import ModelRouterError, ner_extract

_REGEX_PATTERNS: Dict[str, "re.Pattern[str]"] = {
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "credit_card": re.compile(
        r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})\b"
    ),
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    "phone": re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
}

# GLiNER labels for the PII escalation pass, deliberately distinct from
# entities.py's NER_LABELS (which target contract structure, not privacy).
_PII_NER_LABELS = ["person name", "physical address"]
_NER_CATEGORY_MAP = {"person name": "person", "physical address": "address"}


@dataclass
class RedactionResult:
    redacted_text: str
    # category -> count of spans masked. Counts only, never the matched
    # values themselves -- this is what's safe to write to an audit log.
    categories_found: Dict[str, int] = field(default_factory=dict)


def _regex_redact(text: str) -> Tuple[str, Dict[str, int]]:
    counts: Dict[str, int] = {}
    for category, pattern in _REGEX_PATTERNS.items():
        text, n = pattern.subn(f"[REDACTED:{category.upper()}]", text)
        if n:
            counts[category] = n
    return text, counts


def _ner_redact(original_text: str, text: str) -> Tuple[str, Dict[str, int]]:
    """Runs NER against the *original* text (so span text still matches what's
    actually in the contract) and masks each hit in the already regex-redacted
    `text`. Fail-soft: any router error leaves `text` untouched."""
    try:
        result = ner_extract(original_text, _PII_NER_LABELS)
    except ModelRouterError:
        return text, {}

    counts: Dict[str, int] = {}
    # Longest matches first so a full name isn't partially masked by a
    # shorter overlapping span before the full replacement runs.
    entities = sorted(result.entities, key=lambda e: len(e["text"]), reverse=True)
    for e in entities:
        category = _NER_CATEGORY_MAP.get(e["type"])
        span = e["text"].strip()
        if not category or not span or span not in text:
            continue
        n = text.count(span)
        text = text.replace(span, f"[REDACTED:{category.upper()}]")
        counts[category] = counts.get(category, 0) + n
    return text, counts


def redact_pii(text: str) -> RedactionResult:
    """Public entrypoint. Never raises -- the GLiNER escalation degrades to
    the regex floor alone on any error, and an empty/whitespace input just
    passes through unchanged."""
    if not get_settings().PII_REDACTION_ENABLED or not text:
        return RedactionResult(redacted_text=text)

    redacted, counts = _regex_redact(text)
    if get_settings().NER_ENABLED:
        redacted, ner_counts = _ner_redact(text, redacted)
        for category, n in ner_counts.items():
            counts[category] = counts.get(category, 0) + n

    return RedactionResult(redacted_text=redacted, categories_found=counts)
