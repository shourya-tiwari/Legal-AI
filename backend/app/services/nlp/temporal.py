# backend/app/services/nlp/temporal.py
"""
Temporal expression extraction, split into two kinds on purpose:

- Absolute dates ("January 1, 2025", "12/31/2025") get normalized to an ISO
  date via `dateparser.parse()`.
- Durations ("30 days", "twelve months") are reported as-is with NO resolved
  date. dateparser's own `search_dates()` will "resolve" a bare duration
  relative to *today's wall-clock date* (i.e. "30 days from now"), which is
  wrong here — a contract's "30 days" is relative to some other clause's
  trigger event (e.g. the Effective Date), not to whenever this pipeline
  happens to run. Reporting it unresolved is more honest than a plausible-
  looking wrong answer.
"""
from __future__ import annotations

import re
from typing import List

import dateparser

from .schema import TemporalExpression

_ABSOLUTE_DATE_RE = re.compile(
    r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)"
    r"\s+[0-9]{1,2},?\s+[0-9]{4}\b"
    r"|\b[0-9]{1,2}/[0-9]{1,2}/[0-9]{2,4}\b"
)
_DURATION_RE = re.compile(
    r"\b([0-9]+|one|two|three|four|five|six|seven|eight|nine|ten|twelve|"
    r"thirty|sixty|ninety)\s+(day|days|week|weeks|month|months|year|years)\b",
    re.IGNORECASE,
)


def extract_temporal_expressions(clause_text: str) -> List[TemporalExpression]:
    results: List[TemporalExpression] = []

    for match in _ABSOLUTE_DATE_RE.finditer(clause_text):
        text = match.group(0)
        parsed = dateparser.parse(text)
        results.append(TemporalExpression(text=text, normalized_date=parsed.date().isoformat() if parsed else None))

    for match in _DURATION_RE.finditer(clause_text):
        results.append(TemporalExpression(text=match.group(0), normalized_date=None))

    return results
