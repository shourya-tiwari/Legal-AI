"""
Tests for the opt-in Gemini-escalation paths in the deontic tagger and
clause classifier (use_ai_escalation=True). generate_content is mocked, so
these don't hit the network either.
"""
from app.services.nlp.clause_classifier import classify_clause_type
from app.services.nlp.deontic import tag_deontic_modality


def test_deontic_escalates_when_no_rule_matches(monkeypatch):
    def fake_generate_content(prompt, **kwargs):
        return '[{"modality": "obligation", "trigger_phrase": "is bound to"}]'

    monkeypatch.setattr("app.services.nlp.deontic.generate_content", fake_generate_content)

    tags = tag_deontic_modality("The Provider is bound to complete the work.", use_ai_escalation=True)
    assert len(tags) == 1
    assert tags[0].modality == "obligation"
    assert tags[0].source == "ai"


def test_deontic_does_not_escalate_when_a_rule_already_matched(monkeypatch):
    calls = []
    monkeypatch.setattr("app.services.nlp.deontic.generate_content", lambda *a, **k: calls.append(1))

    tags = tag_deontic_modality("The Provider shall pay.", use_ai_escalation=True)
    assert calls == []  # generate_content never called
    assert tags[0].source == "rule"


def test_deontic_escalation_off_by_default_returns_empty_for_unmatched_clause():
    tags = tag_deontic_modality("The sky is blue.")
    assert tags == []


def test_clause_classifier_escalates_when_no_keyword_matches(monkeypatch):
    monkeypatch.setattr("app.services.nlp.clause_classifier.generate_content", lambda *a, **k: "payment_terms")

    # Deliberately no keyword from any CLAUSE_TYPE_KEYWORDS list, so the rule
    # path returns None and this actually exercises the escalation branch.
    clause_type, source = classify_clause_type("The parties acknowledge receipt of this document.", use_ai_escalation=True)
    assert clause_type == "payment_terms"
    assert source == "ai"


def test_clause_classifier_ai_result_outside_taxonomy_falls_back_to_other(monkeypatch):
    monkeypatch.setattr("app.services.nlp.clause_classifier.generate_content", lambda *a, **k: "not_a_real_category")

    clause_type, source = classify_clause_type("Some unusual clause.", use_ai_escalation=True)
    assert clause_type == "other"
    assert source == "ai"
