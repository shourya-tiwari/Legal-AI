# backend/app/services/rag/bm25.py
"""
Sparse (keyword-based) retrieval over the knowledge base, using classic BM25
rather than a learned sparse model (SPLADE) -- BM25 is CPU-trivial, has no
training/model-download cost, and catches exact-term/citation matches dense
embedding similarity can miss (docs/v2/AI_STACK.md's rationale for including
a sparse retriever at all). SPLADE is deferred alongside the other
GPU-adjacent upgrades (see docs/v2/ROADMAP.md's GPU Upgrade phase) -- though
note BM25 itself is a legitimate long-term choice, not just a stand-in;
many production hybrid-RAG systems keep BM25 permanently as the sparse leg.
"""
from __future__ import annotations

import re
from functools import lru_cache
from typing import List, Tuple

from rank_bm25 import BM25Okapi

from .corpus import LEGAL_KNOWLEDGE_BASE, LegalKnowledgeEntry

_WORD_RE = re.compile(r"[a-zA-Z0-9']+")


def _stem(token: str) -> str:
    """A deliberately crude suffix-stripping stemmer -- not a real stemmer
    (Porter/Snowball), but enough to fix the concrete failure mode that
    prompted it: exact-token BM25 matching "deposit" in a query against
    "deposits" in the corpus and finding no match at all. Good enough for
    this small, hand-curated corpus; would need a real stemmer (or the
    dense/embedding leg to carry more weight) at real corpus scale."""
    if len(token) > 4 and token.endswith("ies"):
        return token[:-3] + "y"
    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def _tokenize(text: str) -> List[str]:
    return [_stem(t) for t in _WORD_RE.findall(text.lower())]


class BM25Index:
    def __init__(self, entries: List[LegalKnowledgeEntry]):
        self.entries = entries
        self._bm25 = BM25Okapi([_tokenize(e.text) for e in entries]) if entries else None

    def search(self, query: str, k: int = 3) -> List[Tuple[LegalKnowledgeEntry, float]]:
        if self._bm25 is None:
            return []
        scores = self._bm25.get_scores(_tokenize(query))
        ranked = sorted(zip(self.entries, scores), key=lambda pair: pair[1], reverse=True)
        return [(entry, score) for entry, score in ranked[:k] if score > 0]


@lru_cache
def get_bm25_index() -> BM25Index:
    return BM25Index(LEGAL_KNOWLEDGE_BASE)
