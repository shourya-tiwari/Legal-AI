import re
from typing import Dict, List

RISKY_TERMS: Dict[str, str] = {
    "indemnify": "Potential liability concern",
    "penalty": "May indicate financial risk",
    "late fee": "Additional charges if payment is delayed",
    "breach": "Violation of contract terms",
    "terminate": "Contract termination risk",
    "liability": "Potential responsibility for loss or damage",
    "damages": "Risk of financial penalty",
    "dispute resolution": "May require arbitration or litigation",
    "arbitration": "Binding dispute resolution mechanism",
    "waiver": "Possible loss of rights",
    "default": "Failure to fulfill obligations",
    "deposit forfeiture": "Loss of security deposit",
    "cancellation": "Termination rights and penalties",
    "force majeure": "Excused non-performance due to extraordinary events",
    "confidentiality breach": "Risk of exposing sensitive information",
    "extension denial": "No right to extend contract",
    "renewal obligation": "Mandatory contract renewal terms",
    "limitation of liability": "Caps on damages recoverable",
    "damages cap": "Limit on financial liability",
    "governing law": "Jurisdiction controlling contract interpretation",
    "jurisdiction": "Legal authority over disputes",
    "subrogation": "Rights to claim from third parties",
    "hold harmless": "Agreement to assume liability",
    "insurance requirements": "Required insurance coverage to mitigate risk",
    "non-compete": "Restricts certain business activities",
    "exclusivity": "Limits parties to a single agreement or supplier",
    "termination for convenience": "Allows termination without cause",
    "assignment restriction": "Limits transfer of contractual rights",
    "security deposit": "Funds held to secure obligations",
    "rent escalation": "Terms for increasing rent",
    "renewal period": "Length and conditions of contract renewal",
    "notice requirements": "Formal communication obligations",
    "proprietary": "May restrict use or sharing of confidential or owned information",
    "best efforts": "Vague obligation, unclear standard of performance",
    "reasonable efforts": "Ambiguous level of obligation, may differ by context",
    "commercially reasonable": "Subjective and open to interpretation",
    "material adverse change": "Broad clause, often undefined, triggering major rights",
    "time is of the essence": "Strict deadlines with serious consequences if missed",
    "without prejudice": "Statement made without affecting legal rights",
    "to the fullest extent permitted by law": "Very broad liability-shifting clause",
    "successors and assigns": "Extends obligations to future parties",
    "severability": "Allows remainder of contract to survive if part is invalid",
    "injunctive relief": "Court order requiring or preventing an action",
    "equitable remedies": "Non-monetary remedies such as injunctions or specific performance",
    "notwithstanding": "Overrides other contract provisions (can cause confusion)",
    "hereto": "Old-fashioned legal term meaning 'to this document'",
    "hereinafter": "Means 'from this point forward in the document'",
    "thereof": "Refers back to something previously stated (often vague)",
    "whereas": "Introductory recital, may affect interpretation",
    "forthwith": "Means immediately, but not always strictly defined",
    "per diem": "Daily rate or penalty",
    "liquidated damages": "Pre-set damages amount, sometimes unenforceable if excessive",
    "sole discretion": "Gives one party complete decision-making power",
    "good faith": "Ambiguous standard, hard to enforce",
    "as is": "No warranties or guarantees about condition",
}


# Category taxonomy for the Risk Dashboard spider/radar chart (docs/v2/
# ROADMAP.md Phase 8 "Risk Dashboard spider/radar chart -- closes the V1
# README promise"; docs/v2/FRONTEND.md flagged this as the specific missing
# piece: "risk_radar/rules.py's risky-term list has no category taxonomy
# for a spider chart's axes"). A separate mapping, not a change to
# RISKY_TERMS' own shape -- RISKY_TERMS is used elsewhere (training data
# prep, tests) as a flat {term: explanation} dict, and changing that shape
# would be a breaking change for no benefit when a parallel lookup works
# just as well. Every term in RISKY_TERMS has exactly one category here,
# verified by a test that diffs the two dicts' keysets.
RISK_CATEGORIES: Dict[str, str] = {
    # Liability & Indemnification
    "indemnify": "Liability & Indemnification",
    "liability": "Liability & Indemnification",
    "damages": "Liability & Indemnification",
    "limitation of liability": "Liability & Indemnification",
    "damages cap": "Liability & Indemnification",
    "hold harmless": "Liability & Indemnification",
    "subrogation": "Liability & Indemnification",
    "liquidated damages": "Liability & Indemnification",
    "insurance requirements": "Liability & Indemnification",
    # Termination & Renewal
    "terminate": "Termination & Renewal",
    "cancellation": "Termination & Renewal",
    "termination for convenience": "Termination & Renewal",
    "renewal obligation": "Termination & Renewal",
    "renewal period": "Termination & Renewal",
    "extension denial": "Termination & Renewal",
    "default": "Termination & Renewal",
    "breach": "Termination & Renewal",
    # Payment & Financial
    "penalty": "Payment & Financial",
    "late fee": "Payment & Financial",
    "security deposit": "Payment & Financial",
    "deposit forfeiture": "Payment & Financial",
    "rent escalation": "Payment & Financial",
    "per diem": "Payment & Financial",
    # Confidentiality & IP
    "confidentiality breach": "Confidentiality & IP",
    "proprietary": "Confidentiality & IP",
    # Dispute Resolution & Jurisdiction
    "dispute resolution": "Dispute Resolution & Jurisdiction",
    "arbitration": "Dispute Resolution & Jurisdiction",
    "governing law": "Dispute Resolution & Jurisdiction",
    "jurisdiction": "Dispute Resolution & Jurisdiction",
    "injunctive relief": "Dispute Resolution & Jurisdiction",
    "equitable remedies": "Dispute Resolution & Jurisdiction",
    "without prejudice": "Dispute Resolution & Jurisdiction",
    # Restrictive Covenants
    "non-compete": "Restrictive Covenants",
    "exclusivity": "Restrictive Covenants",
    "assignment restriction": "Restrictive Covenants",
    "successors and assigns": "Restrictive Covenants",
    # Ambiguous Language
    "best efforts": "Ambiguous Language",
    "reasonable efforts": "Ambiguous Language",
    "commercially reasonable": "Ambiguous Language",
    "material adverse change": "Ambiguous Language",
    "sole discretion": "Ambiguous Language",
    "good faith": "Ambiguous Language",
    "notwithstanding": "Ambiguous Language",
    "hereto": "Ambiguous Language",
    "hereinafter": "Ambiguous Language",
    "thereof": "Ambiguous Language",
    "whereas": "Ambiguous Language",
    "forthwith": "Ambiguous Language",
    "as is": "Ambiguous Language",
    "time is of the essence": "Ambiguous Language",
    "to the fullest extent permitted by law": "Ambiguous Language",
    "severability": "Ambiguous Language",
    # Compliance & Force Majeure
    "force majeure": "Compliance & Force Majeure",
    "waiver": "Compliance & Force Majeure",
    "notice requirements": "Compliance & Force Majeure",
}

RISK_CATEGORY_NAMES: List[str] = sorted(set(RISK_CATEGORIES.values()))


def normalize_text(text: str) -> str:
    return re.sub(r"[^\w\s]", "", text.lower())

def find_keyword_flags(clause_text: str, risky_terms: Dict[str, str]) -> List[dict]:
    normalized = normalize_text(clause_text)
    flags: List[dict] = []
    for term, explanation in risky_terms.items():
        # The term itself must go through the same normalization as the
        # text it's matched against -- a real bug, found while building the
        # Risk Dashboard (LEARNING_LOG.md #52): "non-compete" (the only
        # hyphenated entry in RISKY_TERMS) could never match, because
        # normalize_text() strips the hyphen from clause_text ("noncompete")
        # while the un-normalized term still searched for the literal
        # hyphen. This has been live and silently broken since the term was
        # added -- every real "non-compete" clause this scanner has ever
        # been run against was invisible to it.
        pattern = rf"\b{re.escape(normalize_text(term))}\b"
        if re.search(pattern, normalized):
            flags.append({"term": term, "predefined_explanation": explanation})
    return flags