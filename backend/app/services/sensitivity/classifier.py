# backend/app/services/sensitivity/classifier.py
"""
Rule-based document sensitivity classifier.

Assigns the highest tier any signal argues for; `internal` is the
conservative default (a document with no markers is assumed internal, not
public -- you have to *prove* a document is safe to send outside, never
assume it). Every decision carries the phrases that drove it, so an
org-admin reviewing an override sees exactly why.
"""
from __future__ import annotations

import re
from typing import List, Optional

from pydantic import BaseModel, Field

from app.config import get_settings

# ---- tier ordering (higher index = more restrictive) --------------------
_TIER_ORDER = ["public", "internal", "confidential", "privileged"]


def _rank(tier: str) -> int:
    try:
        return _TIER_ORDER.index(tier)
    except ValueError:
        return _TIER_ORDER.index("internal")


class SensitivitySignal(BaseModel):
    tier: str                       # the tier this signal argues for
    phrase: str                     # the matched text (truncated)
    category: str                   # "privilege" | "confidentiality" | "pii" | "public_marker" | "filename"


class SensitivityAssessment(BaseModel):
    tier: str = "internal"
    source: str = "auto"            # "auto" | "override"
    signals: List[SensitivitySignal] = Field(default_factory=list)
    rationale: str = ""


# ---- signal patterns ---------------------------------------------------

_PRIVILEGED_RES = [
    re.compile(r"attorney[-\s]client\s+privilege", re.I),
    re.compile(r"privileged\s*(?:and|&)\s*confidential", re.I),
    re.compile(r"attorney\s+work[-\s]?product", re.I),
    re.compile(r"work[-\s]product\s+(?:doctrine|privilege|protection)", re.I),
    re.compile(r"prepared\s+in\s+anticipation\s+of\s+litigation", re.I),
    re.compile(r"subject\s+to\s+(?:the\s+)?(?:legal|attorney[-\s]client)\s+privilege", re.I),
    re.compile(r"protected\s+by\s+the\s+attorney[-\s]client\s+privilege", re.I),
    re.compile(r"\bprivileged\s+communication\b", re.I),
]

# "strong" confidentiality phrases -- one hit is enough
_CONFIDENTIAL_STRONG_RES = [
    re.compile(r"strictly\s+confidential", re.I),
    re.compile(r"\btrade\s+secret", re.I),
    re.compile(r"proprietary\s+and\s+confidential", re.I),
    re.compile(r"confidential\s+and\s+proprietary", re.I),
    re.compile(r"non[-\s]?disclosure\s+agreement", re.I),
    re.compile(r"\bmutual\s+nda\b", re.I),
    re.compile(r"personally\s+identifiable\s+information", re.I),
    re.compile(r"\b(?:PHI|HIPAA)\b"),
    re.compile(r"protected\s+health\s+information", re.I),
    re.compile(r"classified\s+information", re.I),
]
# a plain "confidential" mention -- weak; needs volume to matter
_CONFIDENTIAL_WEAK_RE = re.compile(r"\bconfidential(?:ity)?\b", re.I)
_CONFIDENTIAL_WEAK_THRESHOLD = 3

_PII_RES = {
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "ein": re.compile(r"\b\d{2}-\d{7}\b"),
    "dob": re.compile(r"\b(?:date\s+of\s+birth|DOB)\b", re.I),
    "passport": re.compile(r"\bpassport\s+(?:no\.?|number|#)", re.I),
    "credit_card": re.compile(r"\b(?:\d[ -]?){13,16}\b(?!\d)"),
}
_PII_DISTINCT_THRESHOLD = 2

_PUBLIC_RES = [
    re.compile(r"for\s+immediate\s+release", re.I),
    re.compile(r"\bpress\s+release\b", re.I),
    re.compile(r"\bpublic\s+(?:filing|record|disclosure)\b", re.I),
    re.compile(r"filed\s+with\s+the\s+(?:SEC|Securities\s+and\s+Exchange)", re.I),
    re.compile(r"\bForm\s+(?:10-K|10-Q|8-K|S-1)\b"),
    re.compile(r"\bEDGAR\b"),
    re.compile(r"available\s+to\s+the\s+(?:general\s+)?public", re.I),
]

_FILENAME_HINTS = {
    "privileged": "privileged",
    "attorney": "privileged",
    "confidential": "confidential",
    "nda": "confidential",
    "non-disclosure": "confidential",
    "press-release": "public",
    "public": "public",
}

_MAX_PHRASE = 80


def is_enabled() -> bool:
    return get_settings().SENSITIVITY_ENABLED


def _sig(tier: str, match: str, category: str) -> SensitivitySignal:
    return SensitivitySignal(tier=tier, phrase=match[:_MAX_PHRASE].strip(), category=category)


def classify_sensitivity(text: str, *, filename: Optional[str] = None) -> SensitivityAssessment:
    default_tier = get_settings().DEFAULT_SENSITIVITY_TIER
    if not is_enabled():
        return SensitivityAssessment(tier=default_tier, source="auto",
                                     rationale="sensitivity classification disabled")

    text = text or ""
    signals: List[SensitivitySignal] = []

    for rx in _PRIVILEGED_RES:
        m = rx.search(text)
        if m:
            signals.append(_sig("privileged", m.group(0), "privilege"))

    for rx in _CONFIDENTIAL_STRONG_RES:
        m = rx.search(text)
        if m:
            signals.append(_sig("confidential", m.group(0), "confidentiality"))
    weak_hits = len(_CONFIDENTIAL_WEAK_RE.findall(text))
    if weak_hits >= _CONFIDENTIAL_WEAK_THRESHOLD:
        signals.append(_sig("confidential", f'{weak_hits}x "confidential"', "confidentiality"))

    distinct_pii = [name for name, rx in _PII_RES.items() if rx.search(text)]
    if len(distinct_pii) >= _PII_DISTINCT_THRESHOLD:
        signals.append(_sig("confidential", f"PII: {', '.join(distinct_pii)}", "pii"))

    for rx in _PUBLIC_RES:
        m = rx.search(text)
        if m:
            signals.append(_sig("public", m.group(0), "public_marker"))

    if filename:
        low = filename.lower()
        for needle, tier in _FILENAME_HINTS.items():
            if needle in low:
                signals.append(_sig(tier, f"filename ~ {needle}", "filename"))

    # Resolve: the most restrictive tier any signal argues for. A `public`
    # signal only wins if NOTHING argues for a higher tier (markers of
    # openness don't override markers of sensitivity).
    upgrade_tiers = [s.tier for s in signals if _rank(s.tier) > _rank("internal")]
    has_public = any(s.tier == "public" for s in signals)

    if upgrade_tiers:
        tier = max(upgrade_tiers, key=_rank)
        drivers = [s.phrase for s in signals if s.tier == tier]
        rationale = f"{tier}: {'; '.join(drivers[:4])}"
    elif has_public and not upgrade_tiers:
        tier = "public"
        rationale = "public: " + "; ".join(s.phrase for s in signals if s.tier == "public")[:200]
    else:
        tier = default_tier
        rationale = f"{default_tier} (no sensitivity markers found)"

    return SensitivityAssessment(tier=tier, source="auto", signals=signals, rationale=rationale)
