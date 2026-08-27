# backend/app/services/rag/hybrid.py
"""
Hybrid retrieval: BM25 (sparse) + Gemini-embedding FAISS (dense), merged by
reciprocal rank fusion (RRF) -- docs/v2/AI_STACK.md's hybrid retrieval
design, minus the self-hosted BGE-M3/bge-reranker-v2-m3 models (deferred to
the GPU Upgrade phase; Gemini's embedding API stands in for the dense signal
today, same rationale as the Model Router's Tier 2 fallback elsewhere).

RRF (not a learned reranker) combines the two rankings: score(entry) =
sum over each retriever's result list of 1 / (K + rank), K=60 is the
standard constant from the original RRF paper (Cormack et al. 2009) -- it's
not being tuned here, just used as published.
"""
from __future__ import annotations

from typing import Dict, List

from app.services.contextualizer.rag import SimpleFaissIndex

from .bm25 import get_bm25_index
from .corpus import LEGAL_KNOWLEDGE_BASE, LegalKnowledgeEntry

RRF_K = 60

_dense_index: SimpleFaissIndex | None = None
_text_to_entry: Dict[str, LegalKnowledgeEntry] = {e.text: e for e in LEGAL_KNOWLEDGE_BASE}


def get_dense_index() -> SimpleFaissIndex:
    global _dense_index
    if _dense_index is None:
        _dense_index = SimpleFaissIndex.from_texts([e.text for e in LEGAL_KNOWLEDGE_BASE])
    return _dense_index


def hybrid_search(query: str, k: int = 3) -> List[LegalKnowledgeEntry]:
    bm25_hits = get_bm25_index().search(query, k=max(k * 2, 6))
    dense_hits = get_dense_index().search(query, k=max(k * 2, 6))

    rrf_scores: Dict[str, float] = {}
    for rank, (entry, _score) in enumerate(bm25_hits, start=1):
        rrf_scores[entry.text] = rrf_scores.get(entry.text, 0.0) + 1.0 / (RRF_K + rank)
    for rank, (text, _distance) in enumerate(dense_hits, start=1):
        rrf_scores[text] = rrf_scores.get(text, 0.0) + 1.0 / (RRF_K + rank)

    ranked_texts = sorted(rrf_scores.keys(), key=lambda t: rrf_scores[t], reverse=True)
    return [_text_to_entry[t] for t in ranked_texts[:k] if t in _text_to_entry]
