# backend/app/services/memory/episodic.py
"""
Episodic-tier memory (docs/v2/AGENTS.md's Memory system): per-document,
across-sessions history -- "last time this document was analyzed, these N
risks were flagged." Backed by the `CaseAnalysis` table that already
exists (app/db_models.py, Phase 7's review queue) rather than a new table:
that data already IS this tier's structured half, and duplicating it would
be exactly the "written twice, drifts once" mistake this project has
already named and fixed before (LEARNING_LOG.md #33's shared-faithfulness-
module extraction is the precedent for "one source of truth, not a copy").

`find_similar_past_analyses` is the "+ the vector store" (embedded
summaries) half docs/v2/AGENTS.md's memory table names -- the same embed-
then-cosine-similarity approach app/services/consistency.py already
established for cross-document clause matching, applied here to analysis
summaries instead of clause text.
"""
from __future__ import annotations

from typing import List, Optional

import numpy as np
from sqlalchemy.orm import Session

from app.db_models import CaseAnalysis
from app.services.model_router import embed_content

_CANDIDATE_LIMIT = 50  # bounds the embedding cost, same shape as consistency.py's MAX_OTHER_DOCUMENTS
_DEFAULT_SIMILARITY_THRESHOLD = 0.6


def get_document_episodic_history(db: Session, org_id: int, document_id: int, *, limit: int = 5) -> List[CaseAnalysis]:
    """Every past analysis run for this document, most recent first.
    `id.desc()` is an explicit tiebreaker, not decoration -- SQLite's
    `CURRENT_TIMESTAMP` has second-level resolution, so two rows committed
    within the same second sort ambiguously on `created_at` alone (the
    exact hazard `routes/models.py`'s eval-runs query already hit and
    fixed the same way, `LEARNING_LOG.md` #32)."""
    return (
        db.query(CaseAnalysis)
        .filter_by(org_id=org_id, document_id=document_id)
        .order_by(CaseAnalysis.created_at.desc(), CaseAnalysis.id.desc())
        .limit(limit)
        .all()
    )


def find_similar_past_analyses(
    db: Session,
    org_id: int,
    summary_text: str,
    *,
    exclude_document_id: Optional[int] = None,
    top_k: int = 3,
    similarity_threshold: float = _DEFAULT_SIMILARITY_THRESHOLD,
) -> List[dict]:
    """Has this org's episodic memory seen an analysis with a similar
    summary before, on a *different* document? Returns
    [{case_analysis_id, document_id, summary, similarity}, ...],
    highest-similarity first."""
    if not summary_text.strip():
        return []

    candidates = (
        db.query(CaseAnalysis)
        .filter(CaseAnalysis.org_id == org_id, CaseAnalysis.summary != "")
        .order_by(CaseAnalysis.created_at.desc(), CaseAnalysis.id.desc())
        .limit(_CANDIDATE_LIMIT)
        .all()
    )
    if exclude_document_id is not None:
        candidates = [c for c in candidates if c.document_id != exclude_document_id]
    if not candidates:
        return []

    texts = [summary_text] + [c.summary for c in candidates]
    result = embed_content(texts, task="embed_corpus")
    vecs = np.array([e.values for e in result.embeddings], dtype="float64")
    query_vec = vecs[0]
    candidate_vecs = vecs[1:]

    query_norm = query_vec / (np.linalg.norm(query_vec) or 1.0)
    matches = []
    for candidate, vec in zip(candidates, candidate_vecs):
        vec_norm = vec / (np.linalg.norm(vec) or 1.0)
        similarity = float(query_norm @ vec_norm)
        if similarity >= similarity_threshold:
            matches.append({
                "case_analysis_id": candidate.id,
                "document_id": candidate.document_id,
                "summary": candidate.summary,
                "similarity": similarity,
            })

    matches.sort(key=lambda m: m["similarity"], reverse=True)
    return matches[:top_k]
