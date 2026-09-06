# backend/app/services/simulation.py
"""
Simulation agent -- the deterministic discrete-event baseline named in
docs/v2/ROADMAP.md Phase 8 ("Simulation agent (deterministic discrete-event
baseline -> Monte-Carlo NOVELTY.md #2)").

`NOVELTY.md` #2's full vision walks the knowledge graph's `TRIGGERED_BY`
edges (conditional obligation logic extracted across a portfolio) and
Monte-Carlo-samples uncertain triggers to surface *emergent*, multi-contract
risk. Neither of those exist yet: `kg/schema.py` explicitly does not model
`Obligation` nodes or `TRIGGERED_BY` edges (the deontic tagger doesn't
resolve actor/action, so that graph would be guessing), and there is no
uncertainty model to sample from. Building the full version on top of a
graph schema that doesn't exist would be building on a guess.

What's real and buildable now, from data the NLP pipeline already extracts:
every clause with an *absolute, resolved* date (`temporal.py` deliberately
never resolves a bare duration like "30 days" against today's wall-clock
date -- see its docstring) is a genuine scheduled event. This walks those
events for one document, classifies each as past / upcoming (within a
warning window) / future relative to a reference date, and returns them in
chronological order -- a real discrete-event timeline, just a single-
document one with no conditional-trigger logic yet. That richer version is
gated on the KG schema growing `Obligation`/`TRIGGERED_BY` first.
"""
from __future__ import annotations

import datetime
from typing import List, Optional

from pydantic import BaseModel

from app.db_models import Document
from app.services.nlp.pipeline import build_clause_objects

DEFAULT_WARNING_WINDOW_DAYS = 30


class SimulatedEvent(BaseModel):
    clause_id: int
    clause_type: str
    date: str  # ISO date
    date_text: str  # the original expression, e.g. "December 31, 2025"
    clause_text: str
    modality: str  # deontic modality if any, else "none"
    status: str  # "past" | "upcoming" | "future", relative to the reference date


def simulate_obligation_timeline(
    document: Document,
    *,
    reference_date: Optional[datetime.date] = None,
    warning_window_days: int = DEFAULT_WARNING_WINDOW_DAYS,
    sensitivity: str = "internal",
) -> List[SimulatedEvent]:
    """Deterministic, no randomness: for a given reference date, every
    clause-level absolute date gets classified as past/upcoming/future.
    "Upcoming" means within `warning_window_days` of the reference date --
    the discrete-event trigger a real simulator would fire an alert on."""
    today = reference_date or datetime.date.today()
    clauses = build_clause_objects(document.full_text, sensitivity=sensitivity)

    events: List[SimulatedEvent] = []
    for clause in clauses:
        modalities = sorted({tag.modality for tag in clause.deontic_tags})
        modality = "/".join(modalities) if modalities else "none"
        for expr in clause.temporal_expressions:
            if not expr.normalized_date:
                continue  # unresolved duration -- honestly skipped, not guessed
            event_date = datetime.date.fromisoformat(expr.normalized_date)
            days_from_today = (event_date - today).days
            if days_from_today < 0:
                status = "past"
            elif days_from_today <= warning_window_days:
                status = "upcoming"
            else:
                status = "future"
            events.append(SimulatedEvent(
                clause_id=clause.id,
                clause_type=clause.clause_type,
                date=expr.normalized_date,
                date_text=expr.text,
                clause_text=clause.text,
                modality=modality,
                status=status,
            ))

    events.sort(key=lambda e: e.date)
    return events
