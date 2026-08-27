"""
Tests for the Phase 2 CPU-only NLP pipeline (backend/app/services/nlp/).
All rule-based (use_ai_escalation defaults to False), so these need no
network access or API key.
"""
from app.services.nlp.ambiguity import detect_ambiguity
from app.services.nlp.clause_classifier import classify_clause_type
from app.services.nlp.cross_references import find_cross_references
from app.services.nlp.deontic import tag_deontic_modality_rule_based
from app.services.nlp.defined_terms import extract_defined_terms, find_term_usages
from app.services.nlp.entities import extract_entities
from app.services.nlp.pipeline import build_clause_objects
from app.services.nlp.segmentation import segment_into_clauses
from app.services.nlp.temporal import extract_temporal_expressions

SAMPLE_CONTRACT = """This Service Agreement ("Agreement") is made on January 1, 2025, between Alpha Solutions Pvt. Ltd. ("Provider") and Beta Enterprises LLP ("Client").

The Provider shall indemnify and hold harmless the Client against all claims arising from Section 4.2 breaches, using commercially reasonable efforts.

The Client may terminate this Agreement with 30 days written notice. The Provider shall not disclose any confidential information.

This Agreement is governed by the laws of the State of California. The total fee is $5,000 payable within thirty days.

It shall maintain insurance coverage as described in Exhibit A.
"""


def test_segmentation_splits_on_blank_lines():
    clauses = segment_into_clauses(SAMPLE_CONTRACT)
    assert len(clauses) == 5


def test_segmentation_splits_long_paragraph_on_sentences():
    long_paragraph = "One sentence here. " * 100  # ~2000 chars, over the default limit
    clauses = segment_into_clauses(long_paragraph, max_clause_chars=200)
    assert len(clauses) > 1
    assert all(len(c) <= 220 for c in clauses)  # small slack for the trailing sentence


def test_extract_defined_terms_finds_paren_and_means_patterns():
    terms = extract_defined_terms(SAMPLE_CONTRACT)
    assert "Agreement" in terms
    assert "Provider" in terms
    assert "Client" in terms


def test_find_term_usages_matches_whole_words_only():
    terms = {"Client": "..."}
    assert find_term_usages("The Client shall pay.", terms) == ["Client"]
    assert find_term_usages("The Clientele shall pay.", terms) == []


def test_cross_reference_detection():
    refs = find_cross_references("As described in Section 4.2 and Exhibit A.")
    texts = {r.text for r in refs}
    assert "Section 4.2" in texts
    assert "Exhibit A" in texts


def test_entity_extraction_money_and_jurisdiction():
    entities = extract_entities("The fee is $5,000 under the laws of the State of California.")
    types_and_texts = {(e.type, e.text) for e in entities}
    assert ("money", "$5,000") in types_and_texts
    assert ("jurisdiction", "California") in types_and_texts


def test_temporal_absolute_date_is_normalized():
    exprs = extract_temporal_expressions("This ends on December 31, 2025.")
    assert any(e.normalized_date == "2025-12-31" for e in exprs)


def test_temporal_duration_is_reported_without_a_misleading_resolved_date():
    exprs = extract_temporal_expressions("Payable within 30 days of the Effective Date.")
    duration = next(e for e in exprs if "30 days" in e.text)
    assert duration.normalized_date is None


def test_deontic_prohibition_not_double_tagged_as_obligation():
    tags = tag_deontic_modality_rule_based("The Provider shall not disclose confidential information.")
    modalities = [t.modality for t in tags]
    assert modalities == ["prohibition"]


def test_deontic_detects_permission_and_obligation_separately():
    tags = tag_deontic_modality_rule_based("The Client may terminate. The Provider shall comply.")
    modalities = {t.modality for t in tags}
    assert modalities == {"permission", "obligation"}


def test_clause_classifier_rule_based_indemnification():
    clause_type, source = classify_clause_type("The Provider shall indemnify and hold harmless the Client.")
    assert clause_type == "indemnification"
    assert source == "rule"


def test_clause_classifier_falls_back_to_other_without_escalation():
    clause_type, source = classify_clause_type("The sky is blue and the grass is green.")
    assert clause_type == "other"
    assert source == "rule"


def test_ambiguity_detection():
    flags = detect_ambiguity("The Provider shall use commercially reasonable efforts.")
    terms = {f.term for f in flags}
    assert "commercially reasonable" in terms


def test_pipeline_produces_one_clause_object_per_segment_with_no_ai_calls():
    clauses = build_clause_objects(SAMPLE_CONTRACT)
    assert len(clauses) == 5
    assert all(c.clause_type_source == "rule" for c in clauses)
    ids = [c.id for c in clauses]
    assert ids == list(range(1, 6))


def test_pipeline_pronoun_candidates_only_flagged_when_no_own_defined_term():
    clauses = build_clause_objects(SAMPLE_CONTRACT)
    last_clause = clauses[-1]  # "It shall maintain insurance..." names no defined term of its own
    assert last_clause.pronoun_candidates
    first_clause = clauses[0]  # names its own defined terms explicitly
    assert first_clause.pronoun_candidates == []
