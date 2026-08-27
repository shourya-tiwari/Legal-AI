# backend/app/services/rag/corpus.py
"""
The Contextualizer's knowledge base -- extends V1's hardcoded, uncited
LEGAL_KNOWLEDGE_BASE list (docs/v1/FEATURES.md flagged this exact gap) into
entries with an explicit citation field.

Citations are given ONLY where reasonably confident and easily verifiable
(a specific, stable statute/regulation) -- most contract-law concepts here
are general common-law doctrine or vary meaningfully by jurisdiction, and get
`citation=None` rather than an invented section number. This is a modest,
illustrative knowledge base for grounding retrieval, not a comprehensive or
authoritative legal database -- every entry should still be read with the
Contextualizer's existing "verify locally" guardrail (see templates.py).
"""
from __future__ import annotations

from pydantic import BaseModel


class LegalKnowledgeEntry(BaseModel):
    text: str
    topic: str  # "lease" | "employment" | "contract_law" | "financial" | "saas"
    citation: str | None = None  # None when there's no single reliable controlling citation


LEGAL_KNOWLEDGE_BASE: list[LegalKnowledgeEntry] = [
    # ---- Lease/Rental Law ----
    LegalKnowledgeEntry(
        topic="lease", citation="Cal. Civ. Code § 1950.5",
        text="California security deposits for residential rentals are capped at one month's rent for most rentals (as amended effective July 1, 2024); small-landlord exceptions exist.",
    ),
    LegalKnowledgeEntry(
        topic="lease", citation="Cal. Civ. Code §§ 1946.2, 1947.12, 1947.13",
        text="California's Tenant Protection Act (AB 1482) caps annual rent increases at 5% plus local CPI (up to 10% max) for many rental units and requires just-cause for termination of certain tenancies; local ordinances may impose additional limits.",
    ),
    LegalKnowledgeEntry(
        topic="lease", citation=None,
        text="Non-refundable fees must generally map to a specific service provided; security deposits are refundable less lawful deductions for damages beyond normal wear and tear.",
    ),
    LegalKnowledgeEntry(
        topic="lease", citation=None,
        text="Landlord entry for non-emergency purposes generally requires advance notice (commonly 24-48 hours depending on jurisdiction); emergency entry is typically allowed without notice.",
    ),
    LegalKnowledgeEntry(
        topic="lease", citation=None,
        text="Tenants generally have a right to habitable premises, privacy, and protection from retaliation for exercising legal rights (e.g., reporting code violations).",
    ),
    LegalKnowledgeEntry(
        topic="lease", citation=None,
        text="Notice periods for lease termination vary by jurisdiction and lease type; month-to-month tenancies commonly require 30-60 days notice.",
    ),

    # ---- Employment Law ----
    LegalKnowledgeEntry(
        topic="employment", citation="Cal. Bus. & Prof. Code § 16600",
        text="California broadly voids non-compete clauses restraining a person from engaging in a lawful profession, trade, or business, with narrow statutory exceptions (e.g., sale of a business).",
    ),
    LegalKnowledgeEntry(
        topic="employment", citation="29 U.S.C. § 207 (FLSA)",
        text="Under the federal Fair Labor Standards Act, non-exempt employees are generally entitled to overtime pay of at least 1.5x their regular rate for hours worked over 40 in a workweek; state law may be more protective.",
    ),
    LegalKnowledgeEntry(
        topic="employment", citation=None,
        text="Confidentiality obligations in employment agreements can survive termination of employment; the scope and duration of what counts as confidential information should be clearly defined.",
    ),
    LegalKnowledgeEntry(
        topic="employment", citation=None,
        text="At-will employment generally allows either party to terminate the relationship without cause, subject to exceptions for protected classes and statutorily protected activity.",
    ),
    LegalKnowledgeEntry(
        topic="employment", citation=None,
        text="Work product created during employment, within the scope of employment, is typically owned by the employer; agreements should clarify ownership of inventions and creative works made outside that scope.",
    ),

    # ---- General Contract Law ----
    LegalKnowledgeEntry(
        topic="contract_law", citation=None,
        text="Contract formation generally requires an offer, acceptance, consideration, and mutual intent to be bound; requirements vary somewhat by jurisdiction and contract type.",
    ),
    LegalKnowledgeEntry(
        topic="contract_law", citation=None,
        text="A breach of contract is a failure to perform as promised without legal excuse; typical remedies include compensatory damages, specific performance, or termination of the contract.",
    ),
    LegalKnowledgeEntry(
        topic="contract_law", citation=None,
        text="Force majeure clauses excuse performance due to unforeseeable circumstances beyond a party's reasonable control; the scope of covered events depends entirely on the contract's specific language.",
    ),
    LegalKnowledgeEntry(
        topic="contract_law", citation=None,
        text="Liquidated damages clauses set pre-agreed damages for breach; courts in many jurisdictions will not enforce them if the amount is unreasonable relative to actual anticipated harm (an unenforceable penalty).",
    ),
    LegalKnowledgeEntry(
        topic="contract_law", citation=None,
        text="A governing law clause specifies which jurisdiction's substantive law applies to interpreting and enforcing the contract; it does not by itself determine where a dispute must be litigated (that's typically a separate venue/forum clause).",
    ),
    LegalKnowledgeEntry(
        topic="contract_law", citation=None,
        text="Arbitration is generally faster and more private than litigation but limits a party's appeal rights; whether an arbitration clause is enforceable can depend on jurisdiction-specific consumer/employment protections.",
    ),

    # ---- Financial Contracts ----
    LegalKnowledgeEntry(
        topic="financial", citation=None,
        text="Interest rates on loans must comply with applicable usury laws, which vary significantly by jurisdiction and loan type; variable-rate provisions should specify the adjustment mechanism and any caps.",
    ),
    LegalKnowledgeEntry(
        topic="financial", citation=None,
        text="Late fees must generally be a reasonable estimate of actual harm rather than a penalty; specific reasonable ranges vary by jurisdiction and contract type.",
    ),
    LegalKnowledgeEntry(
        topic="financial", citation=None,
        text="Acceleration clauses allow a lender to demand full repayment upon a default; notice-and-cure requirements before acceleration vary by agreement and jurisdiction.",
    ),
    LegalKnowledgeEntry(
        topic="financial", citation=None,
        text="A personal guarantee makes an individual personally liable for a business's obligations, potentially exposing personal assets beyond what the business entity itself would risk.",
    ),

    # ---- Technology/SaaS Contracts ----
    LegalKnowledgeEntry(
        topic="saas", citation="Regulation (EU) 2016/679 (GDPR)",
        text="The EU General Data Protection Regulation imposes obligations on processing personal data of EU residents, including lawful-basis, data-subject-rights, and (often) data processing agreement requirements between controllers and processors.",
    ),
    LegalKnowledgeEntry(
        topic="saas", citation="Cal. Civ. Code § 1798.100 et seq. (CCPA/CPRA)",
        text="The California Consumer Privacy Act (as amended by the CPRA) grants California residents rights over their personal information and imposes disclosure and opt-out obligations on covered businesses.",
    ),
    LegalKnowledgeEntry(
        topic="saas", citation=None,
        text="Service level agreements (SLAs) define uptime commitments, performance metrics, and remedies (often service credits) for failing to meet them; remedies are frequently the customer's sole recourse for service failures.",
    ),
    LegalKnowledgeEntry(
        topic="saas", citation=None,
        text="Intellectual property licensing terms should clarify the scope of permitted use, any field-of-use or territory restrictions, and who owns improvements or derivative works.",
    ),
    LegalKnowledgeEntry(
        topic="saas", citation=None,
        text="Limitation of liability clauses cap recoverable damages, but often carve out exceptions for gross negligence, willful misconduct, or breach of confidentiality -- the carve-outs matter as much as the cap itself.",
    ),
]
