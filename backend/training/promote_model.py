# backend/training/promote_model.py
"""
Eval-gated model promotion (docs/v2/ROADMAP.md Phase 8 -- "Eval-gated model
promotion wired into CI/CD").

The training scripts (`train_sensitivity_classifier.py`, `train_risk_model.py`,
and the GPU-blocked clause/deontic heads) each already evaluate a freshly
trained model against a real hand-labelled gold set and write
`models/<name>_eval.json` carrying `passed_cutover_gate` -- the same
meet-or-beat-baseline rule `app/eval/cutover_gate.py` enforces for Model
Router tasks. What was missing was a *gate*: nothing stopped a model whose
`passed_cutover_gate` is false from being wired into production anyway, and
nothing in CI checked it.

This module is that gate. `promoted.json` (committed) is the manifest of
which trained artifacts are approved for production use. `--check` (run in
CI) fails the build if the manifest and the eval results disagree:

  * a model marked `promoted: true` whose `<name>_eval.json` is missing,
    or whose `passed_cutover_gate` is false  -> ERROR (exit 1)
  * a model whose eval PASSED but which isn't promoted                 -> note
  * a `.joblib` artifact with no eval json at all                      -> warn

`--promote <name>` flips a model to promoted -- but only if its eval json
says `passed_cutover_gate` is true (or `--force`, which is logged loudly and
meant only for a documented, reviewed exception). It also copies the
artifact to the stable `models/promoted/<name>.joblib` path an application
loader would read, and (if `mlflow` is installed) transitions the model's
newest registered version to the "Production" stage.

Runtime consumers read the manifest through `app/services/trained_models.py`
(`is_promoted(name)`) -- today nothing does, because neither shipped model
passed its gate, which is exactly the state this gate is supposed to keep
honest.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import logging
import shutil
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s promote_model: %(message)s")
log = logging.getLogger("legalai.training.promote")

TRAINING_DIR = Path(__file__).resolve().parent
MODELS_DIR = TRAINING_DIR / "models"
PROMOTED_DIR = MODELS_DIR / "promoted"
MANIFEST_PATH = TRAINING_DIR / "promoted.json"

# name -> the joblib artifact the training script writes (relative to MODELS_DIR)
KNOWN_MODELS: dict[str, str] = {
    "sensitivity_classifier": "sensitivity_classifier.joblib",
    "risk_model": "risk_model.joblib",
}


def load_manifest() -> dict:
    if not MANIFEST_PATH.exists():
        return {"models": {}}
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def save_manifest(manifest: dict) -> None:
    manifest["updated_at"] = _dt.datetime.now(_dt.timezone.utc).isoformat()
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def eval_path(name: str) -> Path:
    return MODELS_DIR / f"{name}_eval.json"


def load_eval(name: str) -> dict | None:
    p = eval_path(name)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def is_promoted(name: str) -> bool:
    entry = load_manifest().get("models", {}).get(name)
    return bool(entry and entry.get("promoted"))


def promoted_models() -> list[str]:
    return [n for n, e in load_manifest().get("models", {}).items() if e.get("promoted")]


# --------------------------------------------------------------------------- #
# check (CI gate)
# --------------------------------------------------------------------------- #
def check() -> int:
    """Return 0 if the manifest is consistent with the eval results, 1 if not.
    Prints every finding."""
    manifest = load_manifest()
    models = manifest.get("models", {})
    errors: list[str] = []
    notes: list[str] = []

    for name, entry in models.items():
        ev = load_eval(name)
        if entry.get("promoted"):
            if ev is None:
                errors.append(f"{name}: promoted=true but models/{name}_eval.json is missing")
                continue
            if not ev.get("passed_cutover_gate"):
                errors.append(
                    f"{name}: promoted=true but passed_cutover_gate is "
                    f"{ev.get('passed_cutover_gate')!r} in {name}_eval.json"
                )
            else:
                promoted_artifact = PROMOTED_DIR / f"{name}.joblib"
                if not promoted_artifact.exists():
                    errors.append(
                        f"{name}: promoted=true and gate passed, but the promoted "
                        f"artifact {promoted_artifact.relative_to(TRAINING_DIR)} is missing "
                        f"(re-run: python -m training.promote_model --promote {name})"
                    )
                else:
                    notes.append(f"{name}: promoted, gate passed ({_score_str(ev)}) [OK]")
        else:
            if ev is not None and ev.get("passed_cutover_gate"):
                notes.append(
                    f"{name}: eval PASSED ({_score_str(ev)}) but not promoted -- "
                    f"run: python -m training.promote_model --promote {name}"
                )
            elif ev is not None:
                notes.append(f"{name}: not promoted, eval did not pass ({_score_str(ev)}) [expected]")
            else:
                notes.append(f"{name}: not promoted, no eval json yet")

    # Any known artifact with no manifest entry / no eval at all
    for name, artifact in KNOWN_MODELS.items():
        if name not in models and (MODELS_DIR / artifact).exists():
            notes.append(f"{name}: {artifact} exists but has no promoted.json entry -- add one")

    for n in notes:
        log.info(n)
    for e in errors:
        log.error(e)

    if errors:
        log.error("promotion gate: %d inconsistency(ies) -- failing", len(errors))
        return 1
    log.info("promotion gate: OK (%d model(s) in manifest, %d promoted)",
             len(models), len(promoted_models()))
    return 0


def _score_str(ev: dict) -> str:
    for model_key, base_key in (
        ("classical_model_gold_accuracy", "rule_baseline_gold_accuracy"),
        ("classical_model_gold_accuracy", "heuristic_baseline_gold_accuracy"),
        ("candidate_score", "baseline_score"),
    ):
        if model_key in ev and base_key in ev:
            return f"model={ev[model_key]} vs baseline={ev[base_key]}"
    return "scores n/a"


# --------------------------------------------------------------------------- #
# promote / demote
# --------------------------------------------------------------------------- #
def promote(name: str, *, force: bool = False) -> int:
    ev = load_eval(name)
    if ev is None:
        log.error("%s: no models/%s_eval.json -- train and evaluate the model first", name, name)
        return 1
    passed = bool(ev.get("passed_cutover_gate"))
    if not passed and not force:
        log.error(
            "%s: passed_cutover_gate is false (%s) -- refusing to promote. "
            "Re-train to beat the baseline, or pass --force for a documented, reviewed exception.",
            name, _score_str(ev),
        )
        return 1
    if not passed and force:
        log.warning("%s: --force -- promoting a model that did NOT pass its eval gate (%s)",
                    name, _score_str(ev))

    artifact = MODELS_DIR / KNOWN_MODELS.get(name, f"{name}.joblib")
    manifest = load_manifest()
    entry = {
        "promoted": True,
        "promoted_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "passed_cutover_gate": passed,
        "forced": bool(force and not passed),
        "eval": {k: ev[k] for k in ev if k != "gold_predictions"},
    }

    if artifact.exists():
        PROMOTED_DIR.mkdir(parents=True, exist_ok=True)
        dest = PROMOTED_DIR / f"{name}.joblib"
        shutil.copy2(artifact, dest)
        entry["artifact"] = str(dest.relative_to(TRAINING_DIR))
        log.info("copied %s -> %s", artifact.name, dest.relative_to(TRAINING_DIR))
        _mlflow_transition(name, stage="Production")
    else:
        log.warning("%s: %s not on disk (dvc pull?) -- manifest updated, artifact copy skipped",
                    name, artifact.name)

    manifest.setdefault("models", {})[name] = entry
    save_manifest(manifest)
    log.info("%s: promoted", name)
    return 0


def demote(name: str) -> int:
    manifest = load_manifest()
    entry = manifest.get("models", {}).get(name)
    if not entry:
        log.error("%s: not in the manifest", name)
        return 1
    entry["promoted"] = False
    entry["demoted_at"] = _dt.datetime.now(_dt.timezone.utc).isoformat()
    dest = PROMOTED_DIR / f"{name}.joblib"
    if dest.exists():
        dest.unlink()
        log.info("removed %s", dest.relative_to(TRAINING_DIR))
    _mlflow_transition(name, stage="Archived")
    save_manifest(manifest)
    log.info("%s: demoted", name)
    return 0


def _mlflow_transition(name: str, *, stage: str) -> None:
    try:
        import mlflow
        from mlflow.tracking import MlflowClient
    except Exception:
        return
    db = TRAINING_DIR / "mlruns.db"
    if not db.exists():
        return
    try:
        mlflow.set_tracking_uri(f"sqlite:///{db.resolve().as_posix()}")
        client = MlflowClient()
        versions = client.search_model_versions(f"name='{name}'")
        if not versions:
            return
        newest = max(versions, key=lambda v: int(v.version))
        client.transition_model_version_stage(name=name, version=newest.version, stage=stage)
        log.info("mlflow: %s v%s -> %s", name, newest.version, stage)
    except Exception as e:  # pragma: no cover - mlflow registry is optional
        log.info("mlflow registry transition skipped (%s)", e)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true", help="CI gate: fail if manifest disagrees with eval results")
    g.add_argument("--promote", metavar="NAME", help="promote a model (eval must have passed, or --force)")
    g.add_argument("--demote", metavar="NAME", help="demote a model back out of production")
    g.add_argument("--list", action="store_true", help="print the manifest")
    ap.add_argument("--force", action="store_true", help="with --promote: allow a model that failed its gate")
    args = ap.parse_args()

    if args.check:
        sys.exit(check())
    if args.list:
        print(json.dumps(load_manifest(), indent=2))
        sys.exit(0)
    if args.promote:
        sys.exit(promote(args.promote, force=args.force))
    if args.demote:
        sys.exit(demote(args.demote))


if __name__ == "__main__":
    main()
