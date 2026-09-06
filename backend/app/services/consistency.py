# backend/app/services/consistency.py
"""
Cross-Document Consistency -- the embedding-similarity baseline named in
docs/v2/ROADMAP.md Phase 8 ("Cross-Document Consistency agent
(embedding-similarity baseline -> learned NOVELTY.md #1)").

`app/services/kg/queries.py:find_potential_conflicts` already catches
cross-document obligation/prohibition pairs that share the *same defined
term string*. This catches the case that misses: two clauses that discuss
the same thing in different words (different defined terms, different
phrasing) -- the exact-string KG match structurally cannot see those.

Baseline, not `NOVELTY.md` #1's learned Deontic GAT: a fixed cosine-
similarity threshold over clause embeddings + a rule-based deontic-tag
conflict check, not a trained model. Same limitation as the KG conflict
check (actor/action aren't resolved -- see kg/schema.py's docstring), so a
flagged pair is a candidate for human review, not a confirmed contradiction.

Quality note: similarity is only as semantic as whichever embedding
provider the Model Router actually has configured. On the Class-A hashing
floor (nothing self-hosted configured) this is closer to a lexical-overlap
signal than true semantic similarity -- the same honest caveat as the RAG
dense leg (docs/v2/AI_STACK.md). Real "lexically-dissimilar, semantically
similar" matches need a real embedding model (Class B, TEI/bge-m3) serving.
"""
from __future__ import annotations

import math
from typing import List

from pydantic import BaseModel

from app.db_models import Document
from app.services.model_router import embed_content
from app.services.nlp.pipeline import build_clause_objects
from app.services.nlp.schema import ClauseObject

SIMILARITY_THRESHOLD = 0.72
MAX_OTHER_DOCUMENTS = 20  # bound cost -- this is a baseline, not a scalable index

_CONFLICTING_MODALITY_PAIRS = {
    frozenset({"obligation", "prohibition"}),
    frozenset({"permission", "prohibition"}),
}


class ConsistencyFinding(BaseModel):
    document_id: int
    clause_id: int
    clause_text: str
    other_document_id: int
    other_document_filename: str
    other_clause_id: int
    other_clause_text: str
    similarity: float
    modality: str
    other_modality: str
    is_conflict: bool = False


def _cosine(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def _modalities(clause: ClauseObject) -> List[str]:
    return sorted({tag.modality for tag in clause.deontic_tags})


def _conflicts(modalities: List[str], other_modalities: List[str]) -> bool:
    return any(
        frozenset({m, om}) in _CONFLICTING_MODALITY_PAIRS
        for m in modalities
        for om in other_modalities
    )


def find_cross_document_consistency(
    document: Document,
    other_documents: List[Document],
    *,
    sensitivity: str = "internal",
) -> List[ConsistencyFinding]:
    """Embed every clause carrying a deontic tag in `document` and in each
    of `other_documents`, flag pairs above SIMILARITY_THRESHOLD, and mark
    the ones whose deontic modalities actively conflict. Sorted so
    conflicts surface first, then by similarity."""
    this_clauses = [c for c in build_clause_objects(document.full_text, sensitivity=sensitivity) if c.deontic_tags]
    if not this_clauses:
        return []

    this_embeddings = embed_content([c.text for c in this_clauses], task="embed_corpus").embeddings

    findings: List[ConsistencyFinding] = []
    for other_doc in other_documents[:MAX_OTHER_DOCUMENTS]:
        other_clauses = [c for c in build_clause_objects(other_doc.full_text, sensitivity=sensitivity) if c.deontic_tags]
        if not other_clauses:
            continue
        other_embeddings = embed_content([c.text for c in other_clauses], task="embed_corpus").embeddings

        for i, clause in enumerate(this_clauses):
            modalities = _modalities(clause)
            for j, other_clause in enumerate(other_clauses):
                similarity = _cosine(this_embeddings[i].values, other_embeddings[j].values)
                if similarity < SIMILARITY_THRESHOLD:
                    continue
                other_modalities = _modalities(other_clause)
                findings.append(ConsistencyFinding(
                    document_id=document.id,
                    clause_id=clause.id,
                    clause_text=clause.text,
                    other_document_id=other_doc.id,
                    other_document_filename=other_doc.filename,
                    other_clause_id=other_clause.id,
                    other_clause_text=other_clause.text,
                    similarity=round(similarity, 3),
                    modality="/".join(modalities) or "none",
                    other_modality="/".join(other_modalities) or "none",
                    is_conflict=_conflicts(modalities, other_modalities),
                ))

    findings.sort(key=lambda f: (not f.is_conflict, -f.similarity))
    return findings
