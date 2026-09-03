# backend/app/services/nlp/segmentation.py
"""
Clause segmentation: paragraph boundaries first (blank lines — the same
signal extractor.py's PDF/DOCX/TXT paths already preserve as block
boundaries), then a sentence-aware fallback split for paragraphs too long to
treat as one clause. No ML — a regex sentence boundary heuristic is standard
practice and adequate for this; a real sentence tokenizer is a straightforward
upgrade later without changing this module's interface.
"""
from __future__ import annotations

import re
from typing import List

_PARAGRAPH_SPLIT_RE = re.compile(r"\n\s*\n")
# Split after ./!/? followed by whitespace and a capital letter or opening
# paren — avoids splitting on abbreviations/decimals in the common case
# (e.g. "Section 4.2 states" won't split after "4.").
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z(])")

DEFAULT_MAX_CLAUSE_CHARS = 1000


def segment_into_clauses(full_text: str, max_clause_chars: int = DEFAULT_MAX_CLAUSE_CHARS) -> List[str]:
    paragraphs = [p.strip() for p in _PARAGRAPH_SPLIT_RE.split(full_text or "") if p.strip()]

    clauses: List[str] = []
    for paragraph in paragraphs:
        if len(paragraph) <= max_clause_chars:
            clauses.append(paragraph)
            continue
        clauses.extend(_split_long_paragraph(paragraph, max_clause_chars))

    return clauses


def split_sentences(text: str) -> List[str]:
    """Sentence-level split of a single block of text (same regex heuristic
    the clause splitter uses). Used by the Verifier to check each claim
    sentence of a generated summary against its sources."""
    return [s.strip() for s in _SENTENCE_SPLIT_RE.split(text or "") if s.strip()]


def _split_long_paragraph(paragraph: str, max_chars: int) -> List[str]:
    sentences = _SENTENCE_SPLIT_RE.split(paragraph)
    chunks: List[str] = []
    buffer = ""

    for sentence in sentences:
        candidate = (buffer + " " + sentence).strip() if buffer else sentence
        if len(candidate) <= max_chars:
            buffer = candidate
        else:
            if buffer:
                chunks.append(buffer)
            buffer = sentence

    if buffer:
        chunks.append(buffer)

    return chunks
