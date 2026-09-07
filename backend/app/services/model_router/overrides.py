# backend/app/services/model_router/overrides.py
"""
Admin-settable Class C toggles per task (docs/v2/ROADMAP.md Phase 7
"Provider & Model admin: per-task/tier Class C toggles"). Read on every
routing decision (`router.py::_resolve_chain`), so this is cached like
`policy.py::get_policy()` -- cleared explicitly by the admin write endpoint
(`routes/models.py`), not by a TTL, since a toggle should take effect on
the very next request, not eventually.

Fail-soft: a DB error reading overrides degrades to "no overrides active"
(the static YAML policy's own eligibility decides), never blocks a model
call -- same posture as every other DB-adjacent read in the model router
(`telemetry.py`).
"""
from __future__ import annotations

import logging
from functools import lru_cache
from typing import Dict

logger = logging.getLogger("legalai.model_router.overrides")


@lru_cache
def get_class_c_overrides() -> Dict[str, bool]:
    """{task: class_c_disabled} for every task with an active override row."""
    try:
        from app.db import SessionLocal
        from app.db_models import ModelPolicyOverride

        db = SessionLocal()
        try:
            rows = db.query(ModelPolicyOverride).all()
            return {row.task: row.class_c_disabled for row in rows}
        finally:
            db.close()
    except Exception as e:  # pragma: no cover - defensive, never block a model call
        logger.warning("Could not load Class C overrides (%s); none applied.", e)
        return {}


def is_class_c_disabled_for_task(task: str) -> bool:
    return get_class_c_overrides().get(task, False)


def set_class_c_override(task: str, disabled: bool, reason: str | None = None) -> None:
    """Writes the override and invalidates the cache so the very next
    routing decision sees it -- called by the admin API, not by the router
    itself."""
    from app.db import SessionLocal
    from app.db_models import ModelPolicyOverride

    db = SessionLocal()
    try:
        row = db.query(ModelPolicyOverride).filter_by(task=task).first()
        if row is None:
            row = ModelPolicyOverride(task=task)
            db.add(row)
        row.class_c_disabled = disabled
        row.reason = reason
        db.commit()
    finally:
        db.close()
    get_class_c_overrides.cache_clear()


def clear_class_c_override(task: str) -> bool:
    """Removes the override entirely (reverts to the static policy's own
    eligibility for this task). Returns whether a row actually existed."""
    from app.db import SessionLocal
    from app.db_models import ModelPolicyOverride

    db = SessionLocal()
    try:
        row = db.query(ModelPolicyOverride).filter_by(task=task).first()
        if row is None:
            return False
        db.delete(row)
        db.commit()
        return True
    finally:
        db.close()
        get_class_c_overrides.cache_clear()
