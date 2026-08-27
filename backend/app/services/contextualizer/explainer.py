import logging
from typing import Dict, List, Optional

from app.services.contextualizer.templates import UserContext, build_prompt
from app.services.model_router import generate_content
from app.services.rag.citation_validator import find_invalid_citations
from app.services.rag.corpus import LegalKnowledgeEntry
from app.services.rag.hybrid import hybrid_search

logger = logging.getLogger("legalai.contextualizer.explainer")

# Static fallback, used only if hybrid retrieval (BM25 + dense) returns
# nothing at all for the query -- e.g. a contract_type with no matching
# corpus entries. These carry no citation, by definition (they aren't
# retrieved from anything).
_FALLBACK_HINTS_BY_TYPE: Dict[str, List[str]] = {
    "lease": [
        "Security deposits are typically capped by state law; verify local limits.",
        "Landlords must provide habitable premises and respect tenant privacy rights.",
        "Rent increase limitations may apply depending on jurisdiction and lease terms.",
    ],
    "employment": [
        "Non-compete clauses may be unenforceable in some jurisdictions.",
        "Confidentiality obligations can survive termination; clarify scope.",
        "At-will employment allows termination without cause unless contract specifies otherwise.",
    ],
    "mortgage": [
        "Interest rates must comply with usury laws and state regulations.",
        "Late fees must be reasonable and not constitute penalties.",
        "Acceleration clauses allow full payment demand upon default.",
    ],
    "saas": [
        "Data privacy compliance required under GDPR, CCPA, and other laws.",
        "Service level agreements define uptime and performance expectations.",
        "Intellectual property licensing clarifies scope of use and restrictions.",
    ],
}


def get_rag_hints(contract_type: Optional[str], clause_text: str) -> List[LegalKnowledgeEntry]:
    """Hybrid (BM25 + dense) retrieval over the cited knowledge base
    (services/rag/), falling back to a static, uncited per-contract-type
    hint list only if retrieval returns nothing at all."""
    try:
        query = f"{contract_type} contract {clause_text}" if contract_type else clause_text
        hits = hybrid_search(query, k=3)
        if hits:
            return hits
    except Exception as e:
        logger.warning("Hybrid RAG search failed: %s", e)

    if contract_type:
        fallback_texts = _FALLBACK_HINTS_BY_TYPE.get(contract_type.lower(), [])[:3]
        return [LegalKnowledgeEntry(text=t, topic=contract_type.lower(), citation=None) for t in fallback_texts]

    return []


def generate_contextualized_explanation(clause_text: str, ctx_dict: Dict) -> Dict:
    """Generate contextualized explanation using hybrid RAG, with citations
    traceable back to services/rag/corpus.py."""
    ctx = UserContext(
        role=ctx_dict.get("role", "reader"),
        location=ctx_dict.get("location"),
        contract_type=ctx_dict.get("contract_type"),
        interests=ctx_dict.get("interests"),
        tone=ctx_dict.get("tone", "plain"),
    )

    entries = get_rag_hints(ctx.contract_type, clause_text)
    hint_texts = [e.text for e in entries]

    prompt = build_prompt(clause_text, ctx, hints=hint_texts)
    text = generate_content(prompt)

    invalid_citations = find_invalid_citations(text, num_hints=len(hint_texts))
    if invalid_citations:
        logger.warning("Contextualizer output cited unretrieved hint numbers: %s", invalid_citations)

    return {
        "clause": clause_text,
        "context": ctx_dict,
        "explanation": text or "For you, this means… (no response)",
        "used_hints": hint_texts,
        "citations": [e.model_dump() for e in entries],
        "citation_warning": bool(invalid_citations),
    }
