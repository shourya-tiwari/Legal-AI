# backend/app/services/nlp/deontic.py
"""
Deontic modality tagging: is this clause an obligation ("shall"), permission
("may"), prohibition ("shall not"), or discretion ("in its sole discretion")?
Modal-verb regex is a real, standard starting point for this task in the
legal-NLP literature (docs/v2/NLP.md calls this out as an established
technique, not a novel one) — it's cheap, fully explainable, and gets the
common cases right.

Rule-based tagging (`tag_deontic_modality_rule_based`) is Tier 0: always
runs, no network call, no cost. Gemini escalation (opt-in via
`use_ai_escalation=True`) is a practical, working instance of the tiered
Model Router routing concept from docs/v2/AI_STACK.md — applied here at
clause level: if no modal-verb pattern matched at all, ask Gemini for a
judgment call instead of silently returning nothing. It is OFF by default so
the NLP pipeline's tests (and any caller who wants determinism/speed) don't
depend on a model call.
"""
from __future__ import annotations

import re
from typing import List

from ..model_router import generate_content
from .json_utils import parse_json_safely
from .schema import DeonticTag

# Order matters: check prohibition/discretion before the plain obligation/
# permission patterns, since "shall not" contains "shall" and "may not"
# contains "may".
_PROHIBITION_RE = re.compile(
    r"\b(shall not|must not|is prohibited from|may not|neither party (?:may|shall)|"
    r"no party (?:may|shall)|in no event shall|under no circumstances shall)\b",
    re.IGNORECASE,
)
_DISCRETION_RE = re.compile(r"\b(sole discretion|at its discretion|in its sole judgment)\b", re.IGNORECASE)
_OBLIGATION_RE = re.compile(r"\b(shall|must|is required to|agrees to)\b", re.IGNORECASE)
_PERMISSION_RE = re.compile(r"\b(may|is entitled to|has the right to)\b", re.IGNORECASE)

_RULES = (
    (_PROHIBITION_RE, "prohibition"),
    (_DISCRETION_RE, "discretion"),
    (_OBLIGATION_RE, "obligation"),
    (_PERMISSION_RE, "permission"),
)

_AI_PROMPT_TEMPLATE = """Classify the deontic modality of this legal clause: is it an
obligation, permission, prohibition, or discretion (or a mix)?

Return only a JSON array, no prose: [{{"modality": "obligation|permission|prohibition|discretion", "trigger_phrase": "the exact phrase driving this tag"}}]

Clause: "{clause}"
"""


def tag_deontic_modality_rule_based(clause_text: str) -> List[DeonticTag]:
    tags: List[DeonticTag] = []
    matched_spans = []

    for pattern, modality in _RULES:
        for match in pattern.finditer(clause_text):
            # Skip a span already claimed by an earlier (higher-priority) rule
            # -- avoids "shall not" being tagged as both prohibition and
            # obligation just because it contains "shall".
            if any(match.start() < end and match.end() > start for start, end in matched_spans):
                continue
            matched_spans.append((match.start(), match.end()))
            tags.append(DeonticTag(modality=modality, trigger_phrase=match.group(0), confidence=0.8, source="rule"))

    return tags


def tag_deontic_modality(clause_text: str, use_ai_escalation: bool = False,
                         *, sensitivity: str = "internal") -> List[DeonticTag]:
    tags = tag_deontic_modality_rule_based(clause_text)
    if tags or not use_ai_escalation:
        return tags

    try:
        raw = generate_content(
            _AI_PROMPT_TEMPLATE.format(clause=clause_text),
            task="deontic_escalation",
            sensitivity=sensitivity,
            temperature=0.0,
        )
        data = parse_json_safely(raw)
        if not isinstance(data, list):
            return []
        return [
            DeonticTag(
                modality=item.get("modality", "obligation"),
                trigger_phrase=item.get("trigger_phrase", ""),
                confidence=0.5,
                source="ai",
            )
            for item in data
            if isinstance(item, dict)
        ]
    except Exception:
        return []
