# backend/app/services/memory/consolidation.py
"""
Memory consolidation worker (docs/v2/AGENTS.md's Memory system): promotes
episodic memory into semantic (cross-document, per-org) memory -- a pattern
true across many of an org's documents, not just one. The buildable slice
of the docs' own example ("this org's leases are always California-
governed" is the same shape of claim as "this org's contracts tend to
raise an indemnification risk," just not derivable from today's NLP
pipeline's structured output, which doesn't resolve governing-law clauses
to a normalized jurisdiction).

Privacy-tier gated, unconditionally: docs/v2/AGENTS.md requires "content
from Privileged-tier documents is never promoted into cross-document
semantic memory without explicit org opt-in" -- no opt-in mechanism exists
yet (there's no org-settings model to hang one on), so today's behavior is
the conservative default with the override simply not built, not a silent
gap dressed up as a feature.

No scheduler wired to run this automatically -- there's no job-queue/cron
system in this codebase yet. Callable directly (a script, or a future
scheduled task once one exists).
"""
from __future__ import annotations

from typing import Dict, List, Set

from sqlalchemy.orm import Session

from app.db_models import CaseAnalysis, Document, SemanticMemoryEntry

_PRIVILEGED_TIER = "privileged"
_MIN_OCCURRENCES = 2  # a term seen on only one document isn't a portfolio pattern yet


def consolidate_org_memory(db: Session, org_id: int) -> List[SemanticMemoryEntry]:
    """Scans this org's non-privileged CaseAnalysis history for risk terms
    (`CaseAnalysis.risk_findings`, LEARNING_LOG.md #41) that recur across
    more than one document, and upserts one SemanticMemoryEntry per
    recurring term. Returns the entries written or updated."""
    analyses = (
        db.query(CaseAnalysis)
        .join(Document, Document.id == CaseAnalysis.document_id)
        .filter(CaseAnalysis.org_id == org_id, Document.sensitivity_tier != _PRIVILEGED_TIER)
        .all()
    )

    term_to_documents: Dict[str, Set[int]] = {}
    for analysis in analyses:
        for finding in (analysis.risk_findings or []):
            term = finding.get("term") if isinstance(finding, dict) else None
            if term:
                term_to_documents.setdefault(term, set()).add(analysis.document_id)

    entries = []
    for term, doc_ids in term_to_documents.items():
        if len(doc_ids) < _MIN_OCCURRENCES:
            continue
        entry = db.query(SemanticMemoryEntry).filter_by(org_id=org_id, pattern_key=term).first()
        if entry is None:
            entry = SemanticMemoryEntry(org_id=org_id, pattern_key=term)
            db.add(entry)
        entry.description = f'"{term}" flagged as a risk across {len(doc_ids)} documents in this org.'
        entry.supporting_document_ids = sorted(doc_ids)
        entry.occurrence_count = len(doc_ids)
        entries.append(entry)

    db.commit()
    return entries
