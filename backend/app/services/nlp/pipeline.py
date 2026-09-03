# backend/app/services/nlp/pipeline.py
"""
Orchestrates the NLP stages into the canonical ClauseObject list
(docs/v2/NLP.md). `use_ai_escalation` is off by default: the pipeline is
fully deterministic and network-free unless a caller explicitly opts in to
letting the deontic tagger / clause classifier fall back to Gemini for
clauses the rule-based Tier 0 logic can't confidently handle.
"""
from __future__ import annotations

from typing import List

from .ambiguity import detect_ambiguity
from .clause_classifier import classify_clause_type
from .coref import resolve_pronoun_candidates
from .cross_references import find_cross_references
from .defined_terms import extract_defined_terms, find_term_usages
from .deontic import tag_deontic_modality
from .entities import extract_entities
from .schema import ClauseObject
from .segmentation import segment_into_clauses
from .temporal import extract_temporal_expressions


def build_clause_objects(full_text: str, use_ai_escalation: bool = False,
                         *, sensitivity: str = "internal") -> List[ClauseObject]:
    defined_terms = extract_defined_terms(full_text)
    clause_texts = segment_into_clauses(full_text)

    preceding_terms: List[str] = []
    clauses: List[ClauseObject] = []

    for i, text in enumerate(clause_texts, start=1):
        terms_used = find_term_usages(text, defined_terms)
        clause_type, clause_type_source = classify_clause_type(
            text, use_ai_escalation=use_ai_escalation, sensitivity=sensitivity)

        clauses.append(
            ClauseObject(
                id=i,
                text=text,
                clause_type=clause_type,
                clause_type_source=clause_type_source,
                entities=extract_entities(text),
                defined_terms_used=terms_used,
                cross_references=find_cross_references(text),
                deontic_tags=tag_deontic_modality(
                    text, use_ai_escalation=use_ai_escalation, sensitivity=sensitivity),
                temporal_expressions=extract_temporal_expressions(text),
                ambiguity_flags=detect_ambiguity(text),
                pronoun_candidates=resolve_pronoun_candidates(text, terms_used, preceding_terms),
            )
        )

        for term in terms_used:
            if term not in preceding_terms:
                preceding_terms.append(term)

    return clauses
