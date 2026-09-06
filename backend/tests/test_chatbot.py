"""
app/services/chatbot.py's answer_question(): the QA path now runs the same
faithfulness check the agent Verifier has always run (app/services/
faithfulness.py), instead of returning generate_content()'s output
unchecked. NLI_ENABLED=false (conftest.py) throughout, so these exercise
the lexical-overlap fallback -- see tests/test_nli_faithfulness.py for the
real (non-mocked) NLI head.
"""
from __future__ import annotations

from app.services.chatbot import answer_question


def test_answer_question_reports_faithful_when_answer_matches_context(monkeypatch):
    monkeypatch.setattr(
        "app.services.chatbot.generate_content",
        lambda *a, **k: "The agreement may be terminated with thirty days written notice.",
    )

    result = answer_question(
        "How can this be terminated?",
        "Either party may terminate this agreement with thirty days written notice.",
    )

    assert result.answer == "The agreement may be terminated with thirty days written notice."
    assert result.faithfulness_method == "lexical_fallback"
    assert result.faithful is True
    assert result.unsupported_claims == []


def test_answer_question_flags_an_unfaithful_answer(monkeypatch):
    monkeypatch.setattr(
        "app.services.chatbot.generate_content",
        lambda *a, **k: "Bananas grow on trees in tropical climates.",
    )

    result = answer_question(
        "How can this be terminated?",
        "Either party may terminate this agreement with thirty days written notice.",
    )

    assert result.faithful is False
    assert result.faithfulness_method == "lexical_fallback"


def test_answer_question_response_is_backward_compatible_shape(monkeypatch):
    # Old-style consumers that only read `.answer` (or serialize just that
    # key) keep working -- the new fields are additive, not replacing.
    monkeypatch.setattr("app.services.chatbot.generate_content", lambda *a, **k: "An answer.")

    result = answer_question("A question?", "Some contract context.")

    assert result.answer == "An answer."
    assert hasattr(result, "faithful")
    assert hasattr(result, "faithfulness_method")
    assert hasattr(result, "unsupported_claims")


def test_answer_question_bounds_sources_for_a_long_contract(monkeypatch):
    # A contract far longer than MAX_SOURCE_SENTENCES sentences must not
    # blow up the check or pass the whole document as one source -- confirms
    # select_relevant_sources is actually wired in, not just imported.
    long_context = " ".join(f"This is filler clause number {i} about routine matters." for i in range(200))
    long_context += " Either party may terminate this agreement with thirty days written notice."

    monkeypatch.setattr(
        "app.services.chatbot.generate_content",
        lambda *a, **k: "The agreement may be terminated with thirty days written notice.",
    )

    captured = {}
    from app.services import chatbot as chatbot_module

    real_select = chatbot_module.select_relevant_sources

    def spy(text, corpus, **kwargs):
        sources = real_select(text, corpus, **kwargs)
        captured["sources"] = sources
        return sources

    monkeypatch.setattr(chatbot_module, "select_relevant_sources", spy)

    result = answer_question("How can this be terminated?", long_context)

    assert len(captured["sources"]) <= 15
    assert result.faithful is True
