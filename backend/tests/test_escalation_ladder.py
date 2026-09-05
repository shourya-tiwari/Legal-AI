"""
The Phase 6 escalation ladder (docs/v2/AI_STACK.md "Escalation without a
bigger vendor"): `generate_content(hard=True)` prepends the bigger
self-hosted model (`local-llm-large`) to the routing chain. The router-level
behavior is covered by tests/test_model_router.py -- these test the two
call sites that actually *set* the flag (rewriter.py, chatbot.py), which
had no coverage: a service could silently stop setting `hard=` and nothing
would fail.
"""
from app.services.chatbot import _looks_multihop, answer_question
from app.services.rewriter import _HARD_CHUNK_CHARS, rewrite_text


def _spy():
    calls = []

    def fn(prompt, **kwargs):
        calls.append(kwargs.get("hard"))
        return "output"

    return calls, fn


def test_rewrite_escalates_a_chunk_at_or_above_the_hard_threshold(monkeypatch):
    calls, spy = _spy()
    monkeypatch.setattr("app.services.rewriter.generate_content", spy)

    unit = "The Tenant shall pay rent. "
    long_clause = unit * (_HARD_CHUNK_CHARS // len(unit) + 5)
    assert _HARD_CHUNK_CHARS <= len(long_clause) < 8000  # single chunk, at/above the hard threshold
    rewrite_text(long_clause)

    assert calls == [True]


def test_rewrite_does_not_escalate_a_short_clause(monkeypatch):
    calls, spy = _spy()
    monkeypatch.setattr("app.services.rewriter.generate_content", spy)

    rewrite_text("The Tenant shall pay rent monthly.")

    assert calls == [False]


def test_looks_multihop_flags_comparative_questions():
    assert _looks_multihop("Compare the termination and renewal clauses.")
    assert _looks_multihop("What is the notice period? And what about the fee?")
    assert not _looks_multihop("What is the termination notice period?")


def test_answer_question_escalates_multihop_questions(monkeypatch):
    calls, spy = _spy()
    monkeypatch.setattr("app.services.chatbot.generate_content", spy)

    answer_question("Compare the indemnification and limitation of liability clauses.", "context text")

    assert calls == [True]


def test_answer_question_does_not_escalate_simple_questions(monkeypatch):
    calls, spy = _spy()
    monkeypatch.setattr("app.services.chatbot.generate_content", spy)

    answer_question("What is the termination notice period?", "context text")

    assert calls == [False]
