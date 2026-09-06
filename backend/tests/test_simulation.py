"""
The Simulation agent's deterministic discrete-event baseline
(app/services/simulation.py, docs/v2/ROADMAP.md Phase 8). No mocking
needed -- this is pure date arithmetic over the real (already-tested) NLP
temporal extraction, so these exercise the real pipeline end to end.
"""
import datetime

from app.db_models import Document
from app.services.simulation import simulate_obligation_timeline


def _doc(full_text: str) -> Document:
    d = Document(filename="t.txt", full_text=full_text, org_id=1)
    d.id = 1
    return d


def test_classifies_past_upcoming_and_future_events():
    doc = _doc(
        "This Agreement commenced on January 1, 2020.\n\n"
        "The Tenant shall vacate the premises by January 20, 2026.\n\n"
        "This Agreement expires on December 31, 2026."
    )
    reference = datetime.date(2026, 1, 1)

    events = simulate_obligation_timeline(doc, reference_date=reference, warning_window_days=30)

    assert [e.date for e in events] == ["2020-01-01", "2026-01-20", "2026-12-31"]
    assert events[0].status == "past"
    assert events[1].status == "upcoming"  # 19 days out, within the 30-day window
    assert events[2].status == "future"


def test_unresolved_durations_are_skipped_not_guessed():
    doc = _doc("Either party may terminate this Agreement upon thirty days written notice.")

    events = simulate_obligation_timeline(doc, reference_date=datetime.date(2026, 1, 1))

    # "thirty days" gets extracted as a duration with normalized_date=None
    # (temporal.py deliberately never resolves a bare duration against
    # wall-clock "today") -- honestly produces no event, not a guessed date.
    assert events == []


def test_carries_the_clauses_deontic_modality():
    doc = _doc("The Contractor shall deliver the report by March 1, 2026.")

    events = simulate_obligation_timeline(doc, reference_date=datetime.date(2026, 1, 1))

    assert len(events) == 1
    assert events[0].modality == "obligation"
    assert events[0].clause_type


def test_warning_window_is_configurable():
    doc = _doc("The lease renews on February 15, 2026.")
    reference = datetime.date(2026, 1, 1)  # 45 days before the event

    narrow = simulate_obligation_timeline(doc, reference_date=reference, warning_window_days=30)
    wide = simulate_obligation_timeline(doc, reference_date=reference, warning_window_days=60)

    assert narrow[0].status == "future"
    assert wide[0].status == "upcoming"


def test_no_dated_clauses_produces_no_events():
    doc = _doc("This is a recital with no dates or obligations at all.")

    events = simulate_obligation_timeline(doc, reference_date=datetime.date(2026, 1, 1))

    assert events == []
