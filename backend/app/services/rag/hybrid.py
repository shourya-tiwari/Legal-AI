# backend/app/services/rag/hybrid.py
"""
Hybrid retrieval (docs/v2/AI_STACK.md):

  1. dense   -- embeddings via the Model Router (self-hosted by default in
                Phase 5: sentence-transformers if installed, else the Class A
                hashing embedder; a TEI/Ollama embedding endpoint if
                configured). No longer the Gemini embedding API.
  2. sparse  -- BM25 (rank_bm25), a permanent choice for the sparse leg.
  3. graph   -- optional GraphRAG hits passed in by the caller (clause texts
                pulled from Memgraph by term), folded in as a third ranked list.

  fusion     -- reciprocal rank fusion (RRF, K=60, Cormack et al. 2009).
  rerank     -- optional final re-order via the Model Router's reranker
                (self-hosted cross-encoder if installed, else a Class A
                lexical reranker). Behind Settings.RERANKER_ENABLED.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional, Sequence

from app.config import get_settings
from app.services.contextualizer.rag import SimpleFaissIndex
from app.services.model_router import rerank as router_rerank

from .bm25 import get_bm25_index
from .corpus import LEGAL_KNOWLEDGE_BASE, LegalKnowledgeEntry

logger = logging.getLogger("legalai.rag.hybrid")

RRF_K = 60

_dense_index: SimpleFaissIndex | None = None
_text_to_entry: Dict[str, LegalKnowledgeEntry] = {e.text: e for e in LEGAL_KNOWLEDGE_BASE}


def get_dense_index() -> SimpleFaissIndex:
    global _dense_index
    if _dense_index is None:
        _dense_index = SimpleFaissIndex.from_texts([e.text for e in LEGAL_KNOWLEDGE_BASE])
    return _dense_index


def _rrf_accumulate(scores: Dict[str, float], ranked_texts: Sequence[str]) -> None:
    for rank, text in enumerate(ranked_texts, start=1):
        scores[text] = scores.get(text, 0.0) + 1.0 / (RRF_K + rank)


def _maybe_rerank(query: str, entries: List[LegalKnowledgeEntry], k: int) -> List[LegalKnowledgeEntry]:
    if not entries or not get_settings().RERANKER_ENABLED or len(entries) == 1:
        return entries[:k]
    try:
        result = router_rerank(query, [e.text for e in entries], top_k=k)
        return [entries[i] for i in result.ranking if 0 <= i < len(entries)][:k]
    except Exception as e:  # reranking is a best-effort improvement, never a hard dependency
        logger.warning("Rerank step failed (%s); returning RRF order.", e)
        return entries[:k]


def hybrid_search(
    query: str,
    k: int = 3,
    *,
    graph_hits: Optional[Sequence[str]] = None,
) -> List[LegalKnowledgeEntry]:
    """Fuse BM25 + dense (+ optional graph) via RRF, then optionally rerank.
    `graph_hits` is an ordered list of clause texts retrieved from the
    knowledge graph for this query (see rag.graph_retrieval) -- these come
    from the org's OWN documents, not the static corpus, and are surfaced as
    `topic="portfolio"` entries."""
    pool = max(k * 2, 6)
    bm25_hits = get_bm25_index().search(query, k=pool)
    dense_hits = get_dense_index().search(query, k=pool)

    # text -> entry map for this query, seeded with the static corpus and
    # extended with any graph hits so they're first-class in the output.
    local_map: Dict[str, LegalKnowledgeEntry] = dict(_text_to_entry)
    for text in graph_hits or []:
        local_map.setdefault(text, LegalKnowledgeEntry(text=text, topic="portfolio", citation=None))

    rrf_scores: Dict[str, float] = {}
    _rrf_accumulate(rrf_scores, [entry.text for entry, _ in bm25_hits])
    _rrf_accumulate(rrf_scores, [text for text, _ in dense_hits])
    if graph_hits:
        _rrf_accumulate(rrf_scores, list(graph_hits))

    ranked_texts = sorted(rrf_scores, key=lambda t: rrf_scores[t], reverse=True)
    fused = [local_map[t] for t in ranked_texts if t in local_map][:pool]
    return _maybe_rerank(query, fused, k)
