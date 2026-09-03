# backend/training/_common.py
"""Shared helpers for the data-prep and training scripts. Runs outside the
`app` package on purpose (docs/v2/AI_STACK.md provider-isolation contract only
covers `app/`), so these may import transformers/datasets directly."""
from __future__ import annotations

import json
import logging
import random
import sys
from pathlib import Path
from typing import Dict, Iterable, List

# Make `import app...` work when run as `python training/foo.py` from backend/.
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

DATA_DIR = Path(__file__).resolve().parent / "data"
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("legalai.training")


def write_jsonl(rows: List[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    log.info("wrote %d rows -> %s", len(rows), path)


def read_jsonl(path: Path) -> List[dict]:
    with path.open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def train_val_split(rows: List[dict], val_frac: float = 0.15, seed: int = 13):
    rng = random.Random(seed)
    rows = list(rows)
    rng.shuffle(rows)
    n_val = max(1, int(len(rows) * val_frac))
    return rows[n_val:], rows[:n_val]


def class_balance(rows: Iterable[dict], key: str) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for r in rows:
        v = r[key]
        if isinstance(v, list):
            for item in v:
                counts[item] = counts.get(item, 0) + 1
        else:
            counts[v] = counts.get(v, 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: -kv[1]))


def load_yaml_config(path: str) -> dict:
    import yaml

    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)
