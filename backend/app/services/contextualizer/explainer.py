import logging
from typing import Dict, List, Optional
from app.services.model_router import generate_content
from app.services.contextualizer.templates import UserContext, build_prompt
from app.services.contextualizer.rag import SimpleFaissIndex

logger = logging.getLogger("legalai.contextualizer.explainer")

# Comprehensive legal knowledge base
LEGAL_KNOWLEDGE_BASE = [
    # Lease/Rental Law
    "California AB 12: Security deposits for rental agreements on/after July 1, 2024 are capped at one month's rent for most rentals; small-landlord exceptions exist.",
    "AB 1482: Many California rental units have rent increases capped at 5% + CPI, up to 10% maximum, depending on timing and CPI; check local ordinances for applicability.",
    "Security deposits vs fees: Non-refundable fees must map to specific services; deposits are generally refundable less lawful deductions for damages.",
    "Landlord entry rights: Generally 24-48 hours notice required for non-emergency entry; emergency entry allowed without notice.",
    "Tenant rights: Right to habitable premises, privacy, and protection from retaliation for exercising legal rights.",
    "Lease termination: Notice periods vary by jurisdiction and lease type; typically 30-60 days for month-to-month tenancies.",
    
    # Employment Law
    "Non-compete clauses: May be unenforceable in some jurisdictions (e.g., California); verify current state rules and scope limitations.",
    "Confidentiality obligations: Can survive termination; clarify scope, duration, and what constitutes confidential information.",
    "At-will employment: Either party can terminate without cause unless contract specifies otherwise; exceptions exist for protected classes.",
    "Overtime pay: Generally required for hours over 40 per week unless exempt under FLSA; state laws may be more restrictive.",
    "Workplace harassment: Employers must provide harassment-free environment; policies should include reporting procedures and investigation process.",
    "Intellectual property: Work created during employment typically belongs to employer; clarify ownership of inventions and creative works.",
    
    # General Contract Law
    "Contract formation: Requires offer, acceptance, consideration, and mutual intent; must be legally enforceable.",
    "Breach of contract: Failure to perform as promised; remedies include damages, specific performance, or contract termination.",
    "Force majeure: Excuses performance due to unforeseeable circumstances beyond party's control; scope varies by contract language.",
    "Liquidated damages: Pre-agreed damages for breach; must be reasonable estimate of actual damages, not penalty.",
    "Governing law: Specifies which jurisdiction's laws apply; important for interpretation and enforcement.",
    "Dispute resolution: Arbitration vs litigation; arbitration typically faster and private but limits appeal rights.",
    
    # Financial Contracts
    "Interest rates: Must comply with usury laws; variable rates should specify adjustment mechanism and caps.",
    "Late fees: Must be reasonable and not constitute penalty; typically 1-5% of payment amount.",
    "Acceleration clauses: Allow lender to demand full payment upon default; notice requirements may apply.",
    "Collateral: Security interest in property; perfection requirements vary by asset type and jurisdiction.",
    "Personal guarantees: Individual liability for business obligations; consider impact on personal assets.",
    
    # Technology/SaaS Contracts
    "Data privacy: Compliance with GDPR, CCPA, and other privacy laws; data processing agreements may be required.",
    "Service level agreements: Define uptime, performance metrics, and remedies for service failures.",
    "Intellectual property licensing: Clarify scope of use, restrictions, and ownership of improvements.",
    "Termination rights: Notice periods, data return obligations, and transition assistance requirements.",
    "Limitation of liability: Caps on damages; may not apply to gross negligence or willful misconduct.",
]

# Initialize RAG index
_rag_index: Optional[SimpleFaissIndex] = None

def get_rag_index() -> SimpleFaissIndex:
    """Get or create the RAG index with legal knowledge base."""
    global _rag_index
    if _rag_index is None:
        _rag_index = SimpleFaissIndex.from_texts(LEGAL_KNOWLEDGE_BASE)
    return _rag_index

def get_rag_hints(contract_type: Optional[str], clause_text: str) -> List[str]:
    """Get relevant legal hints using RAG based on contract type and clause content."""
    try:
        rag_index = get_rag_index()
        
        # Create search query combining contract type and clause content
        search_query = clause_text
        if contract_type:
            search_query = f"{contract_type} contract {clause_text}"
        
        # Search for relevant knowledge
        results = rag_index.search(search_query, k=3)
        
        # Extract just the text from results
        hints = [result[0] for result in results if result[0]]
        
        # Fallback to contract-type specific hints if RAG fails
        if not hints and contract_type:
            fallback_hints = {
                "lease": [
                    "Security deposits are typically capped by state law; verify local limits.",
                    "Landlords must provide habitable premises and respect tenant privacy rights.",
                    "Rent increase limitations may apply depending on jurisdiction and lease terms."
                ],
                "employment": [
                    "Non-compete clauses may be unenforceable in some jurisdictions.",
                    "Confidentiality obligations can survive termination; clarify scope.",
                    "At-will employment allows termination without cause unless contract specifies otherwise."
                ],
                "mortgage": [
                    "Interest rates must comply with usury laws and state regulations.",
                    "Late fees must be reasonable and not constitute penalties.",
                    "Acceleration clauses allow full payment demand upon default."
                ],
                "saas": [
                    "Data privacy compliance required under GDPR, CCPA, and other laws.",
                    "Service level agreements define uptime and performance expectations.",
                    "Intellectual property licensing clarifies scope of use and restrictions."
                ]
            }
            hints = fallback_hints.get(contract_type.lower(), [])[:3]
        
        return hints[:3]  # Limit to 3 hints
        
    except Exception as e:
        logger.warning("RAG search failed: %s", e)
        # Return empty list if RAG fails
        return []

def generate_contextualized_explanation(
    clause_text: str,
    ctx_dict: Dict
) -> Dict:
    """Generate contextualized explanation using dynamic RAG."""
    ctx = UserContext(
        role=ctx_dict.get("role", "reader"),
        location=ctx_dict.get("location"),
        contract_type=ctx_dict.get("contract_type"),
        interests=ctx_dict.get("interests"),
        tone=ctx_dict.get("tone", "plain"),
    )
    
    # Get dynamic hints using RAG
    hints = get_rag_hints(ctx.contract_type, clause_text)
    
    # Build prompt with dynamic context
    prompt = build_prompt(clause_text, ctx, hints=hints)
    
    # Generate explanation
    text = generate_content(prompt)
    
    return {
        "clause": clause_text,
        "context": ctx_dict,
        "explanation": text or "For you, this means… (no response)",
        "used_hints": hints,
    }
