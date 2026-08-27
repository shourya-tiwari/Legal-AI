# backend/app/eval/gold_set.py
"""
A small, hand-authored gold set for the rule-based NLP pipeline (clause type
+ deontic modality). This is a deliberately narrow stand-in for the
Ragas + CUAD/ContractNLI-based eval harness described in docs/v2/AI_STACK.md
and docs/v2/ARCHITECTURE.md — that needs downloading and curating a real
external dataset, which is real, separate work (see docs/v2/ROADMAP.md's
Phase 2 exit criteria). What's here is real and runnable now: every example
is representative contract language, and the harness (run_eval.py) reports
genuine precision/recall against it, not a placeholder number.

Extend this list as the rule-based classifiers grow — that's the whole
point of an eval set: it should get harder, not stay static.
"""
from __future__ import annotations

from typing import List, TypedDict


class GoldExample(TypedDict):
    text: str
    expected_clause_type: str
    expected_deontic_modalities: List[str]  # modalities that MUST appear


GOLD_SET: List[GoldExample] = [
    {
        "text": "The Provider shall indemnify and hold harmless the Client against all third-party claims.",
        "expected_clause_type": "indemnification",
        "expected_deontic_modalities": ["obligation"],
    },
    {
        "text": "In no event shall either party's liability exceed the total fees paid under this Agreement.",
        "expected_clause_type": "limitation_of_liability",
        "expected_deontic_modalities": ["prohibition"],
    },
    {
        "text": "Either party may terminate this Agreement upon 30 days written notice to the other party.",
        "expected_clause_type": "termination",
        "expected_deontic_modalities": ["permission"],
    },
    {
        "text": "The Employee shall not disclose any confidential or proprietary information of the Company.",
        "expected_clause_type": "confidentiality",
        "expected_deontic_modalities": ["prohibition"],
    },
    {
        "text": "Neither party may assign this Agreement without the prior written consent of the other party.",
        "expected_clause_type": "assignment",
        "expected_deontic_modalities": ["prohibition"],
    },
    {
        "text": "This Agreement shall be governed by and construed in accordance with the laws of the State of Delaware.",
        "expected_clause_type": "governing_law",
        "expected_deontic_modalities": ["obligation"],
    },
    {
        "text": "Any dispute arising under this Agreement shall be resolved through binding arbitration.",
        "expected_clause_type": "dispute_resolution",
        "expected_deontic_modalities": ["obligation"],
    },
    {
        "text": "Neither party shall be liable for delays caused by force majeure events beyond its reasonable control.",
        "expected_clause_type": "force_majeure",
        "expected_deontic_modalities": ["prohibition"],
    },
    {
        "text": "All intellectual property created during the engagement shall be the sole property of the Company.",
        "expected_clause_type": "ip_ownership",
        "expected_deontic_modalities": ["obligation"],
    },
    {
        "text": "The Client shall pay all invoices within thirty days of the invoice date.",
        "expected_clause_type": "payment_terms",
        "expected_deontic_modalities": ["obligation"],
    },
    {
        "text": "This Agreement shall automatically renew for successive one-year terms unless either party provides notice.",
        "expected_clause_type": "renewal",
        "expected_deontic_modalities": ["obligation"],
    },
    {
        "text": "The Contractor shall maintain commercial general liability insurance coverage throughout the term.",
        "expected_clause_type": "insurance",
        "expected_deontic_modalities": ["obligation"],
    },
    {
        "text": "The parties acknowledge that they have read and understood the terms of this Agreement.",
        "expected_clause_type": "other",
        "expected_deontic_modalities": [],
    },
    {
        "text": "The Landlord may enter the premises at its sole discretion for inspection purposes.",
        "expected_clause_type": "other",
        "expected_deontic_modalities": ["permission", "discretion"],
    },
    {
        "text": "The Tenant must not sublease the premises without the Landlord's prior written approval.",
        "expected_clause_type": "other",
        "expected_deontic_modalities": ["prohibition"],
    },
]
