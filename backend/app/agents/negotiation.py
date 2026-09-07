# backend/app/agents/negotiation.py
"""
Negotiation/Drafting agent -- static org-configured preferences first
(docs/v2/ROADMAP.md Phase 8, docs/v2/AGENTS.md's full vision needs
"procedural memory of the org's negotiation history," which doesn't exist:
no redlining feature or history is tracked anywhere in this codebase, see
`LEARNING_LOG.md` #51's audit before building this).

This is the buildable subset the roadmap itself names: an org configures
its preferred language for a handful of clause types
(`Organization.negotiation_preferences`, `app/routes/org_settings.py`);
this agent compares each extracted clause of a covered type against the
org's preferred language and, when they differ meaningfully, produces a
structured suggestion (via the existing `clause_diff` tool) rather than a
learned redline recommendation. No clause is ever auto-edited -- every
suggestion is routed through `request_human_approval`
(docs/v2/AGENTS.md: "Human approval gate (always, for any suggested edit
sent externally)"), which honestly returns a pending-review marker, not a
blocking call (see tools.py's own docstring on why).

No-ops entirely (zero suggestions, no tool calls) when the org has no
`negotiation_preferences` configured -- the common case today, since no
real org has actually set any yet.
"""
from __future__ import annotations

import re

from .state import AgentStep, CaseState, NegotiationSuggestion
from .tools import call_tool

# This is a "does the clause match the org's stated preferred wording"
# check, not a "how similar are these two clauses in general" check -- a
# fuzzy similarity threshold is the wrong tool here. Verified empirically
# (LEARNING_LOG.md #51) before shipping: "shall be governed by ... State of
# California" vs "... State of Delaware" -- a single-word jurisdiction
# swap that is one of the most legally consequential redlines a contract
# can have -- scores 0.90 on difflib's SequenceMatcher ratio, comfortably
# above any similarity threshold that would still catch genuinely
# different-looking clauses. The same lesson prepare_embedding_data.py's
# hard-negative construction (#49) already learned: textual similarity and
# legal-effect similarity are different axes. So: flag anything that isn't
# the same wording modulo whitespace/case, full stop -- `similarity` is
# still reported for the reviewer's benefit (how small a fix this is), but
# never used to decide whether to flag at all.
def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def run_negotiation_drafting(state: CaseState) -> dict:
    suggestions: list[NegotiationSuggestion] = []

    if state.negotiation_preferences:
        for clause in state.clauses:
            preference = state.negotiation_preferences.get(clause.clause_type)
            if not preference or not preference.get("preferred_language"):
                continue

            preferred_language = preference["preferred_language"]
            if _normalize(clause.text) == _normalize(preferred_language):
                continue  # already the org's preferred wording (modulo whitespace/case)

            diff = call_tool("clause_diff", clause_a=clause.text, clause_b=preferred_language)

            approval = call_tool(
                "request_human_approval",
                payload={
                    "document_id": state.document_id,
                    "clause_id": clause.id,
                    "clause_type": clause.clause_type,
                    "current_language": clause.text,
                    "suggested_language": preferred_language,
                    "similarity": diff.similarity,
                },
                reason=f"Clause deviates from org-preferred {clause.clause_type} language "
                       f"(similarity={diff.similarity:.2f})",
            )

            suggestions.append(NegotiationSuggestion(
                clause_id=clause.id,
                clause_type=clause.clause_type,
                current_language=clause.text,
                suggested_language=preferred_language,
                rationale=preference.get("rationale", ""),
                similarity=diff.similarity,
                diff_lines=diff.diff_lines,
                status=approval.status,
            ))

    step = AgentStep(
        agent_name="negotiation_drafting",
        input_summary=f"{len(state.clauses)} clauses, "
                      f"{len(state.negotiation_preferences)} org preference(s) configured",
        output_summary=f"{len(suggestions)} suggestion(s), each pending human review",
    )
    return {"negotiation_suggestions": suggestions, "trace": state.trace + [step]}
