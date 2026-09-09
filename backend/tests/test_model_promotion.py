"""
Eval-gated model promotion (docs/v2/ROADMAP.md Phase 8) --
`training/promote_model.py` (the CI gate) and `app/services/trained_models.py`
(the runtime reader).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_TRAINING = Path(__file__).resolve().parents[1] / "training"
sys.path.insert(0, str(_TRAINING))

import promote_model  # noqa: E402
from app.services import trained_models  # noqa: E402


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    """Redirect promote_model + trained_models at a throwaway training tree."""
    models = tmp_path / "models"
    models.mkdir()
    manifest = tmp_path / "promoted.json"
    monkeypatch.setattr(promote_model, "TRAINING_DIR", tmp_path)
    monkeypatch.setattr(promote_model, "MODELS_DIR", models)
    monkeypatch.setattr(promote_model, "PROMOTED_DIR", models / "promoted")
    monkeypatch.setattr(promote_model, "MANIFEST_PATH", manifest)
    monkeypatch.setattr(trained_models, "_TRAINING_DIR", tmp_path)
    monkeypatch.setattr(trained_models, "_MANIFEST_PATH", manifest)
    trained_models.reload_manifest()
    yield tmp_path
    trained_models.reload_manifest()


def _write_eval(models_dir: Path, name: str, *, passed: bool) -> None:
    (models_dir / f"{name}_eval.json").write_text(json.dumps({
        "classical_model_gold_accuracy": 0.9 if passed else 0.5,
        "rule_baseline_gold_accuracy": 0.6 if passed else 0.8,
        "passed_cutover_gate": passed,
    }), encoding="utf-8")


# ---- the committed manifest is self-consistent ----

def test_committed_manifest_passes_the_check():
    assert promote_model.check() == 0


def test_committed_manifest_promotes_nothing():
    # Neither classical model beat its baseline -- see LEARNING_LOG.md #43/#45.
    assert promote_model.promoted_models() == []
    assert trained_models.is_promoted("sensitivity_classifier") is False


# ---- promote refuses a model that failed its gate ----

def test_promote_refuses_failed_gate(sandbox):
    models = sandbox / "models"
    _write_eval(models, "risk_model", passed=False)
    promote_model.save_manifest({"models": {"risk_model": {"promoted": False}}})

    assert promote_model.promote("risk_model") == 1  # non-zero -> refused
    assert promote_model.is_promoted("risk_model") is False


def test_promote_force_overrides_but_records_it(sandbox):
    models = sandbox / "models"
    _write_eval(models, "risk_model", passed=False)
    (models / "risk_model.joblib").write_bytes(b"fake joblib")
    promote_model.save_manifest({"models": {}})

    assert promote_model.promote("risk_model", force=True) == 0
    entry = promote_model.load_manifest()["models"]["risk_model"]
    assert entry["promoted"] is True
    assert entry["forced"] is True
    assert (models / "promoted" / "risk_model.joblib").exists()


# ---- promote accepts a model that passed, and check stays green ----

def test_promote_then_check_and_runtime_reader(sandbox):
    models = sandbox / "models"
    _write_eval(models, "sensitivity_classifier", passed=True)
    (models / "sensitivity_classifier.joblib").write_bytes(b"fake joblib")
    promote_model.save_manifest({"models": {}})

    assert promote_model.promote("sensitivity_classifier") == 0
    assert promote_model.check() == 0

    trained_models.reload_manifest()
    assert trained_models.is_promoted("sensitivity_classifier") is True
    path = trained_models.promoted_artifact_path("sensitivity_classifier")
    assert path is not None and path.is_file()


# ---- check catches a manifest that lies ----

def test_check_fails_when_manifest_claims_a_failed_model_is_promoted(sandbox):
    models = sandbox / "models"
    _write_eval(models, "risk_model", passed=False)
    promote_model.save_manifest({"models": {"risk_model": {"promoted": True}}})

    assert promote_model.check() == 1


def test_check_fails_when_promoted_artifact_missing(sandbox):
    models = sandbox / "models"
    _write_eval(models, "risk_model", passed=True)
    promote_model.save_manifest({"models": {"risk_model": {"promoted": True}}})

    # promoted:true + gate passed, but no models/promoted/risk_model.joblib
    assert promote_model.check() == 1


def test_demote_reverts(sandbox):
    models = sandbox / "models"
    _write_eval(models, "sensitivity_classifier", passed=True)
    (models / "sensitivity_classifier.joblib").write_bytes(b"fake")
    promote_model.save_manifest({"models": {}})
    promote_model.promote("sensitivity_classifier")

    assert promote_model.demote("sensitivity_classifier") == 0
    assert promote_model.is_promoted("sensitivity_classifier") is False
    assert not (models / "promoted" / "sensitivity_classifier.joblib").exists()
