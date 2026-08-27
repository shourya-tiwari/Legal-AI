# backend/app/services/nlp/cross_references.py
"""Detects internal cross-references ("Section 4.2", "Exhibit A") within a
clause. This is what the Knowledge Graph's REFERENCES edges (docs/v2/
KNOWLEDGE_GRAPH.md) will eventually be built from, once a graph exists."""
from __future__ import annotations

import re
from typing import List

from .schema import CrossReference

_CROSS_REF_RE = re.compile(
    r"\b(Section|Clause|Article|Exhibit|Schedule|Appendix|Paragraph)\s+"
    r"([0-9]+(?:\.[0-9]+)*|[A-Z])\b"
)


def find_cross_references(clause_text: str) -> List[CrossReference]:
    seen = set()
    refs: List[CrossReference] = []
    for match in _CROSS_REF_RE.finditer(clause_text):
        text = f"{match.group(1)} {match.group(2)}"
        if text not in seen:
            seen.add(text)
            refs.append(CrossReference(text=text))
    return refs
