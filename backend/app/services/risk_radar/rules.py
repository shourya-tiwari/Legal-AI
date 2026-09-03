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


def normalize_text(text: str) -> str:
    return re.sub(r"[^\w\s]", "", text.lower())

def find_keyword_flags(clause_text: str, risky_terms: Dict[str, str]) -> List[dict]:
    normalized = normalize_text(clause_text)
    flags: List[dict] = []
    for term, explanation in risky_terms.items():
        pattern = rf"\b{re.escape(term)}\b"
        if re.search(pattern, normalized):
            flags.append({"term": term, "predefined_explanation": explanation})
    return flags