# backend/app/services/trained_models.py
"""
Read-only view of `backend/training/promoted.json` -- the eval-gated model
promotion manifest (docs/v2/ROADMAP.md Phase 8, written by
`training/promote_model.py`).

This is the single seam application code uses to decide whether a trained
`.joblib` head is approved for production. Today nothing calls it, because
neither shipped classical model (sensitivity, risk severity) beat its
rule/heuristic baseline -- which is exactly the state the promotion gate
exists to keep honest: `is_promoted("sensitivity_classifier")` returns
False, so `app/services/sensitivity/` correctly stays rule-based rather
than silently loading a worse model.

When a future model *does* pass its gate and gets promoted, its loader does:

    from app.services.trained_models import promoted_artifact_path
    path = promoted_artifact_path("sensitivity_classifier")
    if path is not None:
        model = joblib.load(path)          # promoted, safe to use
    else:
        ...                                # fall back to the rule baseline

Fail-soft: a missing/corrupt manifest yields "nothing promoted", never an
exception -- the rule baselines are always a safe fallback.
"""
from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger("legalai.trained_models")

_TRAINING_DIR = Path(__file__).resolve().parents[2] / "training"
_MANIFEST_PATH = _TRAINING_DIR / "promoted.json"


@lru_cache(maxsize=1)
def _manifest() -> dict:
    try:
        return json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"models": {}}
    except Exception as e:  # pragma: no cover - defensive
        logger.warning("trained_models: could not read %s (%s)", _MANIFEST_PATH, e)
        return {"models": {}}


def reload_manifest() -> None:
    """Drop the cached manifest (after a promote/demote in the same process)."""
    _manifest.cache_clear()


def is_promoted(name: str) -> bool:
    entry = _manifest().get("models", {}).get(name)
    return bool(entry and entry.get("promoted"))


def promoted_models() -> list[str]:
    return [n for n, e in _manifest().get("models", {}).items() if e.get("promoted")]


def promoted_artifact_path(name: str) -> Path | None:
    """Absolute path to the promoted `.joblib`, or None if the model isn't
    promoted or its artifact isn't on disk."""
    if not is_promoted(name):
        return None
    entry = _manifest()["models"][name]
    rel = entry.get("artifact") or f"models/promoted/{name}.joblib"
    path = _TRAINING_DIR / rel
    return path if path.is_file() else None
