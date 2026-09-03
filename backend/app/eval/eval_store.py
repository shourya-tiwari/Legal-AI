# backend/app/eval/eval_store.py
"""
Fail-soft writer for the `eval_runs` table (app/db_models.py). Same posture as
app/services/model_router/telemetry.py -- a DB error is logged and swallowed,
never raised, so an eval run still prints its result even with no database.
"""
from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger("legalai.eval.store")


def record_eval_run(
    *,
    task: str,
    dataset: str,
    provider: str,
    model: str,
    metric: str,
    score: float,
    n_examples: int,
    baseline_score: Optional[float] = None,
    passed: Optional[bool] = None,
    notes: Optional[str] = None,
) -> None:
    try:
        from app.db import SessionLocal, init_db
        from app.db_models import EvalRun

        init_db()  # idempotent create_all -- eval scripts run outside the app lifespan
        row = EvalRun(
            task=task, dataset=dataset, provider=provider, model=model, metric=metric,
            score=float(score), n_examples=int(n_examples),
            baseline_score=baseline_score, passed=passed, notes=notes,
        )
        db = SessionLocal()
        try:
            db.add(row)
            db.commit()
        finally:
            db.close()
    except Exception as e:  # pragma: no cover - defensive
        logger.warning("eval_runs persistence skipped (%s)", e)
