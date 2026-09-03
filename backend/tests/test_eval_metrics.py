"""
Pure-stdlib eval scorers (app/eval/metrics.py) -- always runs, no deps.
"""
from __future__ import annotations

from app.eval import metrics


def test_exact_match_normalizes_articles_and_punctuation():
    assert metrics.exact_match("The State of Delaware.", "state of delaware") == 1.0
    assert metrics.exact_match("Delaware", "New York") == 0.0


def test_token_f1_partial_overlap():
    assert metrics.token_f1("the quick brown fox", "the quick brown fox") == 1.0
    assert 0.0 < metrics.token_f1("quick brown fox", "the slow brown fox") < 1.0
    assert metrics.token_f1("apples", "oranges") == 0.0


def test_squad_f1_empty_gold_is_the_not_present_case():
    assert metrics.squad_f1("", []) == 1.0
    assert metrics.squad_f1("None", []) == 1.0
    assert metrics.squad_f1("30 days", []) == 0.0
    assert metrics.squad_f1("within 30 days", ["30 days", "thirty days"]) > 0.4


def test_accuracy_and_macro_f1():
    preds = ["Yes", "No", "Yes", "No"]
    golds = ["Yes", "No", "No", "No"]
    assert metrics.accuracy(preds, golds) == 0.75
    mf1 = metrics.macro_f1(preds, golds, labels=["Yes", "No"])
    assert 0.0 < mf1 < 1.0


def test_macro_f1_perfect_and_zero():
    assert metrics.macro_f1(["a", "b"], ["a", "b"], labels=["a", "b"]) == 1.0
    assert metrics.macro_f1(["a", "a"], ["b", "b"], labels=["a", "b"]) == 0.0
