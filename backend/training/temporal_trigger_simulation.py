# backend/training/temporal_trigger_simulation.py
"""
NOVELTY.md idea #2, "Temporal Obligation Decay Simulation" -- the CPU-only
research-track prototype step (docs/v2/TASKS.md: "Idea #2 ... CPU-only --
prototype auto-constructed simulation, validate against manually-modelled
scenarios").

`app/services/simulation.py` is the shipped Phase 8 baseline: it only
schedules clauses with an *absolute, resolved* date (`temporal.py`
deliberately never resolves a bare duration like "30 days" against
wall-clock "now" -- a duration is relative to some OTHER clause's trigger
event, not to whenever the pipeline happens to run). That baseline's own
docstring names exactly what idea #2 asks for on top of it: "automatic
construction of the simulation model from NLP-extracted conditional
logic" -- i.e. actually resolving "30 days after termination" once you
know when termination happens, instead of leaving it unresolved forever.

This prototype does that at single-document scope, with hand-provided
anchor event dates standing in for "another clause's already-resolved
date" (idea #2's full portfolio vision needs `Obligation`/`TRIGGERED_BY`
graph nodes that don't exist yet -- `simulation.py`'s own docstring names
this as the real, structural blocker for the richer version; this
prototype does NOT attempt that graph, on purpose, so as not to build on
a KG schema that doesn't exist):

  1. extract_conditional_triggers() -- regex over the *existing* clause
     text (no new NLP pipeline stage) for "N days/months/years after/of/
     following <trigger phrase>" patterns -- a genuinely different
     extraction target than temporal.py's absolute-date regex.
  2. auto_construct_simulation() -- given a small dict of known anchor
     event dates (e.g. {"termination": date(...)}), matches each trigger
     rule's phrase against the anchor keywords and computes the derived
     date, producing the same SimulatedEvent shape the shipped baseline
     already uses (additive, not a replacement).

Validated against hand-modelled scenarios in main() -- the actual point
of "validate against manually-modelled scenarios": for each scenario, the
expected derived date is computed by hand in the test data, and the
auto-constructed result is checked against it, not just eyeballed.

    python training/temporal_trigger_simulation.py
"""
from __future__ import annotations

import datetime
import re
from typing import Dict, List, Optional

from dateutil.relativedelta import relativedelta
from pydantic import BaseModel

from _common import log

_UNIT_KWARGS = {"day": "days", "days": "days", "month": "months", "months": "months",
               "year": "years", "years": "years"}

# "within 30 days after termination", "no later than 6 months following the
# Effective Date", "10 days of written notice" -- the connector word
# ("after"/"of"/"from"/"following") is itself part of what distinguishes
# this from an absolute-date expression (temporal.py's own regex targets
# calendar dates like "December 31, 2025", never "N units <connector> X").
_TRIGGER_RE = re.compile(
    r"(\d+)\s+(day|days|month|months|year|years)\s+(?:after|of|from|following)\s+"
    r"([^.,;]+?)(?=[.,;]|$)",
    re.IGNORECASE,
)


class TriggerRule(BaseModel):
    clause_id: int
    duration_amount: int
    duration_unit: str  # "days" | "months" | "years"
    trigger_phrase: str
    source_text: str


class DerivedEvent(BaseModel):
    clause_id: int
    source_text: str
    trigger_phrase: str
    anchor_event: str
    anchor_date: str  # ISO date
    derived_date: str  # ISO date
    derivation: str  # human-readable, e.g. "30 days after termination"


def extract_conditional_triggers(clauses: List) -> List[TriggerRule]:
    """`clauses` is a list of ClauseObject (or anything with `.id`/`.text`).
    Returns every "N units after/of/from/following <phrase>" match --
    genuinely new extraction, not a re-run of temporal.py's absolute-date
    regex, which this deliberately does not touch or duplicate."""
    rules: List[TriggerRule] = []
    for clause in clauses:
        for match in _TRIGGER_RE.finditer(clause.text):
            amount, unit, phrase = match.groups()
            rules.append(TriggerRule(
                clause_id=clause.id,
                duration_amount=int(amount),
                duration_unit=_UNIT_KWARGS[unit.lower()],
                trigger_phrase=phrase.strip().lower(),
                source_text=clause.text,
            ))
    return rules


def auto_construct_simulation(
    rules: List[TriggerRule], anchor_events: Dict[str, datetime.date],
) -> List[DerivedEvent]:
    """For each trigger rule, find an anchor event whose name appears as a
    substring of the trigger phrase (a real, if simple, matching
    heuristic -- "termination" matches a trigger phrase "termination of
    this agreement"), then derive amount+unit from that anchor's date.
    A rule with no matching anchor is honestly skipped, not guessed."""
    derived: List[DerivedEvent] = []
    for rule in rules:
        anchor_name = next((name for name in anchor_events if name in rule.trigger_phrase), None)
        if anchor_name is None:
            continue
        anchor_date = anchor_events[anchor_name]
        delta = relativedelta(**{rule.duration_unit: rule.duration_amount})
        derived_date = anchor_date + delta
        derived.append(DerivedEvent(
            clause_id=rule.clause_id,
            source_text=rule.source_text,
            trigger_phrase=rule.trigger_phrase,
            anchor_event=anchor_name,
            anchor_date=anchor_date.isoformat(),
            derived_date=derived_date.isoformat(),
            derivation=f"{rule.duration_amount} {rule.duration_unit} after {anchor_name}",
        ))
    return derived


# --------------------------------------------------------------------------
# Hand-modelled validation scenarios -- the actual point of this prototype.
# Each scenario's `expected` date is computed by hand (not by running this
# code), so a bug in extract/derive would show up as a real mismatch.
# --------------------------------------------------------------------------

_SCENARIOS = [
    {
        "text": "The Tenant shall vacate the premises within 30 days after termination of this Agreement.",
        "anchors": {"termination": datetime.date(2026, 1, 1)},
        "expected": "2026-01-31",
    },
    {
        "text": "The Buyer shall remit final payment no later than 15 days following the Delivery Date.",
        "anchors": {"the delivery date": datetime.date(2026, 3, 1)},
        "expected": "2026-03-16",
    },
    {
        "text": "Either party may audit the other's records within 6 months of the Effective Date.",
        "anchors": {"the effective date": datetime.date(2025, 6, 1)},
        "expected": "2025-12-01",
    },
    {
        "text": "The Licensee shall return all Confidential Information within 1 year after expiration of this License.",
        "anchors": {"expiration of this license": datetime.date(2027, 1, 1)},
        "expected": "2028-01-01",
    },
    {
        # No matching anchor provided -- should be honestly skipped, not guessed.
        "text": "The Contractor shall submit a final report within 10 days after project completion.",
        "anchors": {},
        "expected": None,
    },
]


def _fake_clause(clause_id: int, text: str):
    from types import SimpleNamespace

    return SimpleNamespace(id=clause_id, text=text)


def run_validation() -> bool:
    all_passed = True
    for i, scenario in enumerate(_SCENARIOS, start=1):
        clause = _fake_clause(i, scenario["text"])
        rules = extract_conditional_triggers([clause])
        derived = auto_construct_simulation(rules, scenario["anchors"])

        if scenario["expected"] is None:
            passed = len(derived) == 0
            log.info("scenario %d: expected no derivation (no anchor) -> %s -- %s",
                     i, "PASS" if passed else "FAIL", scenario["text"][:60])
        else:
            actual = derived[0].derived_date if derived else None
            passed = actual == scenario["expected"]
            log.info("scenario %d: expected=%s actual=%s -> %s -- %s",
                     i, scenario["expected"], actual, "PASS" if passed else "FAIL", scenario["text"][:60])
        all_passed = all_passed and passed
    return all_passed


def main() -> None:
    all_passed = run_validation()
    log.info("all scenarios passed: %s", all_passed)


if __name__ == "__main__":
    main()
