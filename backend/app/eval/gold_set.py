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


class FaithfulnessExample(TypedDict):
    summary: str                 # a claim a generated summary might make
    sources: List[str]           # the retrieved source texts it should be grounded in
    is_faithful: bool            # ground truth: is the summary entailed by the sources?


# Hand-built cases for the Verifier's faithfulness check (app/agents/verifier.py).
# The NLI head must classify these more accurately than the lexical-overlap
# fallback -- especially the "high vocabulary overlap but wrong meaning" cases
# (3, 5) that lexical overlap gets wrong by design.
FAITHFULNESS_GOLD: List[FaithfulnessExample] = [
    {  # 1: exact restatement
        "summary": "The security deposit must be returned within 21 days after the tenant moves out.",
        "sources": ["Under California law the landlord must return the security deposit within 21 days of the tenant vacating the unit."],
        "is_faithful": True,
    },
    {  # 2: valid paraphrase
        "summary": "Either side can end the contract by giving 60 days notice.",
        "sources": ["This Agreement may be terminated by either party upon sixty (60) days prior written notice."],
        "is_faithful": True,
    },
    {  # 3: high lexical overlap, contradicted meaning
        "summary": "The security deposit is returned within 90 days of move-out.",
        "sources": ["The landlord shall return the security deposit within 21 days after the tenant vacates the premises."],
        "is_faithful": False,
    },
    {  # 4: fabricated detail not in sources
        "summary": "The contract automatically renews for five-year terms and cannot be cancelled.",
        "sources": ["This Agreement has an initial term of one year.", "Termination for convenience requires 30 days notice."],
        "is_faithful": False,
    },
    {  # 5: overlapping vocabulary, opposite obligation
        "summary": "The vendor is permitted to disclose confidential information to third parties.",
        "sources": ["The Vendor shall not disclose Confidential Information to any third party without prior written consent."],
        "is_faithful": False,
    },
    {  # 6: supported, different words
        "summary": "The provider covers the customer's legal costs if a third party sues over the provider's IP.",
        "sources": ["The Provider shall indemnify and hold the Customer harmless against any third-party claim that the Services infringe intellectual property rights, including reasonable attorneys' fees."],
        "is_faithful": True,
    },
    {  # 7: claim about a topic the sources don't cover
        "summary": "Late payments accrue interest at 1.5% per month.",
        "sources": ["Invoices are payable within 30 days of receipt.", "The governing law is the State of New York."],
        "is_faithful": False,
    },
    {  # 8: faithful multi-sentence
        "summary": "The agreement is governed by Delaware law. Disputes go to binding arbitration.",
        "sources": ["This Agreement shall be governed by the laws of the State of Delaware.",
                    "Any dispute arising under this Agreement shall be resolved by binding arbitration."],
        "is_faithful": True,
    },
]


class SensitivityExample(TypedDict):
    text: str
    expected_tier: str           # public | internal | confidential | privileged


# Hand-built cases for the document sensitivity classifier
# (app/services/sensitivity/). The gate in tests/test_eval_gate.py holds the
# rule base to >= 90% accuracy here -- raise it as the rules improve.
SENSITIVITY_GOLD: List[SensitivityExample] = [
    {"text": "This memorandum is protected by the attorney-client privilege.", "expected_tier": "privileged"},
    {"text": "PRIVILEGED & CONFIDENTIAL work product prepared in anticipation of litigation.", "expected_tier": "privileged"},
    {"text": "Legal advice memo — subject to the attorney-client privilege, do not forward.", "expected_tier": "privileged"},
    {"text": "MUTUAL NON-DISCLOSURE AGREEMENT. The parties will exchange Confidential Information.", "expected_tier": "confidential"},
    {"text": "The Receiving Party shall not disclose the Disclosing Party's trade secret information.", "expected_tier": "confidential"},
    {"text": "Employee record: SSN 123-45-6789, DOB on file, passport number X1234567.", "expected_tier": "confidential"},
    {"text": "FOR IMMEDIATE RELEASE — the Company announces its results, filed with the SEC on Form 8-K.", "expected_tier": "public"},
    {"text": "This document is available to the general public via the EDGAR system.", "expected_tier": "public"},
    {"text": "MASTER SERVICES AGREEMENT covering consulting deliverables, fees and a payment schedule.", "expected_tier": "internal"},
    {"text": "5. Confidentiality. Each party will protect the other's confidential information with reasonable care.", "expected_tier": "internal"},
    {"text": "Amendment No. 2 to the Lease, adjusting the rent and extending the term by one year.", "expected_tier": "internal"},
]


class RewriteExample(TypedDict):
    text: str
    must_retain: List[str]   # facts (numbers/parties/dates) a correct rewrite keeps
    banned_jargon: List[str]  # legalese a *plain-English* rewrite should not still contain


# Hand-built cases for the Phase 6 cutover gate's `clause_rewrite` eval
# (app/eval/tasks.py:run_rewrite_gold). Free-text generation has no single
# reference paraphrase, so this checks the two properties a good rewrite
# provably has instead of similarity to one hand-written answer: it keeps the
# operative facts, and it actually drops the legalese it was asked to plain-
# English (a rewrite that just keeps "shall"/"notwithstanding" verbatim has
# not done the job, even if it's otherwise a faithful paraphrase).
REWRITE_GOLD: List[RewriteExample] = [
    {
        "text": "The Client shall pay all invoices within thirty (30) days of the invoice date. Notwithstanding the foregoing, any amount not paid when due shall accrue interest at 1.5% per month.",
        "must_retain": ["30 days", "1.5%"],
        "banned_jargon": ["shall", "notwithstanding"],
    },
    {
        "text": "The Contractor shall indemnify and hold harmless the Company from any and all third-party claims, up to a maximum aggregate liability of $500,000.",
        "must_retain": ["$500,000"],
        "banned_jargon": ["shall", "indemnify and hold harmless"],
    },
    {
        "text": "The Employee shall not, during the Term or thereafter, disclose any Confidential Information of the Company to any third party without prior written consent.",
        "must_retain": ["third party", "written consent"],
        "banned_jargon": ["shall", "thereafter"],
    },
    {
        "text": "Notwithstanding anything to the contrary herein, in no event shall either party's aggregate liability under this Agreement exceed the total fees paid in the preceding twelve (12) months.",
        "must_retain": ["12 months"],
        "banned_jargon": ["notwithstanding", "herein", "in no event shall"],
    },
    {
        "text": "This Agreement shall be governed by and construed in accordance with the laws of the State of Delaware, without regard to its conflict of laws principles.",
        "must_retain": ["Delaware"],
        "banned_jargon": ["shall", "construed in accordance with"],
    },
    {
        "text": "Neither party may assign this Agreement, in whole or in part, without the prior written consent of the other party, which consent shall not be unreasonably withheld.",
        "must_retain": ["written consent"],
        "banned_jargon": ["shall"],
    },
    {
        "text": "This Agreement shall automatically renew for successive one (1) year terms unless either party provides written notice of non-renewal at least sixty (60) days prior to the end of the then-current term.",
        "must_retain": ["one", "60 days"],
        "banned_jargon": ["shall", "then-current"],
    },
    {
        "text": "The Landlord shall return the security deposit, less any lawful deductions, within twenty-one (21) days after the Tenant vacates the premises.",
        "must_retain": ["21 days"],
        "banned_jargon": ["shall", "hereinafter"],
    },
]


class TimelineEventGold(TypedDict):
    date_description: str
    event: str


class TimelineGoldExample(TypedDict):
    text: str
    expected_events: List[TimelineEventGold]


# Hand-built cases for the Phase 6 cutover gate's `timeline_extract` eval
# (app/eval/tasks.py:run_timeline_extract_gold). Grading is per-gold-event
# best-match token-F1 (metrics.token_f1) against the model's predicted
# {date_description, event} pairs -- there's no single correct wording, but a
# correct extraction names the same date and the same obligation.
TIMELINE_GOLD: List[TimelineGoldExample] = [
    {
        "text": "This Lease shall commence on January 1, 2025 and expire on December 31, 2025. The Tenant shall pay rent on the first day of each month.",
        "expected_events": [
            {"date_description": "January 1, 2025", "event": "Lease commences"},
            {"date_description": "December 31, 2025", "event": "Lease expires"},
            {"date_description": "first day of each month", "event": "Rent payment due"},
        ],
    },
    {
        "text": "The Buyer shall deposit $50,000 into escrow within five (5) business days of the Effective Date. Closing shall occur no later than March 15, 2026.",
        "expected_events": [
            {"date_description": "within 5 business days of the Effective Date", "event": "Buyer deposits $50,000 into escrow"},
            {"date_description": "March 15, 2026", "event": "Closing occurs"},
        ],
    },
    {
        "text": "Either party may terminate this Agreement upon 90 days written notice. The initial Term begins on the Effective Date and continues for two (2) years.",
        "expected_events": [
            {"date_description": "90 days after written notice", "event": "Agreement terminates"},
            {"date_description": "two years from the Effective Date", "event": "initial Term ends"},
        ],
    },
    {
        "text": "The Employee's probationary period shall end on June 30, 2025, after which full benefits become effective July 1, 2025.",
        "expected_events": [
            {"date_description": "June 30, 2025", "event": "probationary period ends"},
            {"date_description": "July 1, 2025", "event": "full benefits become effective"},
        ],
    },
    {
        "text": "The Contractor shall complete Phase 1 by April 1, 2025, Phase 2 by September 1, 2025, and deliver final materials no later than December 15, 2025.",
        "expected_events": [
            {"date_description": "April 1, 2025", "event": "Phase 1 complete"},
            {"date_description": "September 1, 2025", "event": "Phase 2 complete"},
            {"date_description": "December 15, 2025", "event": "final materials delivered"},
        ],
    },
]


class RiskExample(TypedDict):
    text: str
    expected_terms: List[str]  # phrases a real risk-flag pass should surface


# Hand-built cases for the Phase 6 cutover gate's `risk_analysis` eval
# (app/eval/tasks.py:run_risk_analysis_gold). Scored as recall: of the
# phrases that make each clause genuinely risky, how many does the model's
# {"flags":[{"term","explanation"}]} JSON actually surface (substring match
# over the combined term+explanation text)?
RISK_GOLD: List[RiskExample] = [
    {
        "text": "The Contractor shall indemnify and hold harmless the Company from any and all claims, including consequential and punitive damages, with no cap on liability.",
        "expected_terms": ["no cap on liability", "punitive damages"],
    },
    {
        "text": "Either party may terminate this Agreement immediately, for any reason or no reason, without notice or a cure period.",
        "expected_terms": ["without notice", "no reason"],
    },
    {
        "text": "The Company may unilaterally amend the terms of this Agreement at any time without notifying the Customer.",
        "expected_terms": ["unilaterally amend", "without notifying"],
    },
    {
        "text": "This non-compete restricts the Employee from working in the same industry anywhere in the world for a period of ten (10) years after termination.",
        "expected_terms": ["ten (10) years", "anywhere in the world"],
    },
    {
        "text": "Any dispute shall be resolved exclusively through binding arbitration administered by an arbitrator selected solely by the Company, with each party bearing its own costs.",
        "expected_terms": ["arbitrator selected solely by the Company", "binding arbitration"],
    },
]
