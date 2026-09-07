# backend/training/push_to_argilla.py
"""
Push weak-labelled deontic-modality examples into Argilla for legal-expert
review (docs/v2/ROADMAP.md Phase 8 "Legal-expert review of weak labels in
Argilla").

This script builds the real integration: an Argilla dataset with the four
deontic modalities as a multi-label question, each record pre-filled with
the *existing* rule-teacher's prediction as a `Suggestion` (so a reviewer
confirms/corrects rather than labelling from scratch -- the actual point of
using a review tool instead of a spreadsheet). What it cannot do is the
review itself: **no legal expert is available in this environment** to sit
down and adjudicate the suggestions, so every record's `response` stays
unset after this script runs. That is a genuine, human-availability
blocker, not an infrastructure one -- distinct from whether an Argilla
server can be stood up and pushed to, which this script proves it can.

Requires a running Argilla server (`ARGILLA_API_URL`, default
http://localhost:6900). The commonly-documented single-container
`argilla/argilla-quickstart` image is **stale and incompatible** with the
current (2.x) `argilla` Python client -- verified directly, not assumed:
it serves an old v1.29.1 API (a different, pre-rewrite protocol) and its
own pinned client dependency fails to install on a modern Python/pip
toolchain (`pkg_resources` missing from the build env). The real, verified
way to run a v2-compatible server is `training/argilla-compose.yml`
(Argilla server + Elasticsearch + Redis -- the server needs a Redis
connection for its webhook/task queue even in a single-node setup, which
is undocumented in the “quickstart” framing but was a real, hard startup
failure until added):

    docker compose -f training/argilla-compose.yml up -d
    python training/push_to_argilla.py

A brand-new server has no default workspace -- this script creates one
(`legalai`) on first run rather than requiring it to exist already.

Fails soft with a clear message if the server isn't reachable, the same
posture app/services/kg/client.py and rate_limit.py already establish for
optional backing services -- this script is a one-off data-curation tool,
not something any request path depends on.

    python training/push_to_argilla.py [--n 100] [--dataset-name deontic-review]
"""
from __future__ import annotations

import argparse
import os

from _common import DATA_DIR, log, read_jsonl

_MODALITIES = ["obligation", "permission", "prohibition", "discretion"]


def _ensure_workspace(client, name: str = "legalai"):
    import argilla as rg

    existing = client.workspaces(name=name)
    if existing is not None:
        return existing
    workspace = rg.Workspace(name=name, client=client)
    workspace.create()
    log.info("created workspace %r (a fresh Argilla server has none by default)", name)
    return workspace


def build_dataset(client, name: str, workspace):
    import argilla as rg

    existing = client.datasets(name=name, workspace=workspace)
    if existing is not None:
        log.info("dataset %r already exists -- reusing it", name)
        return existing

    settings = rg.Settings(
        fields=[rg.TextField(name="text")],
        questions=[
            rg.MultiLabelQuestion(
                name="modalities",
                title="Which deontic modalities apply to this sentence?",
                labels=_MODALITIES,
            ),
        ],
        metadata=[
            rg.TermsMetadataProperty(name="source"),
        ],
    )
    dataset = rg.Dataset(name=name, settings=settings, workspace=workspace, client=client)
    dataset.create()
    log.info("created dataset %r in workspace %r", name, workspace.name)
    return dataset


def push_records(dataset, rows: list[dict]) -> int:
    import argilla as rg

    records = []
    for row in rows:
        text = row.get("text", "")
        weak_labels = row.get("labels", [])
        if not text:
            continue
        records.append(rg.Record(
            fields={"text": text},
            suggestions=[
                rg.Suggestion(question_name="modalities", value=weak_labels, agent="rule_teacher")
            ] if weak_labels else [],
            metadata={"source": row.get("source", "unknown")},
        ))
    dataset.records.log(records)
    return len(records)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=100, help="max rows to push")
    ap.add_argument("--dataset-name", default="legalai-deontic-review")
    ap.add_argument("--split", default="deontic_train.jsonl")
    args = ap.parse_args()

    api_url = os.environ.get("ARGILLA_API_URL", "http://localhost:6900")
    api_key = os.environ.get("ARGILLA_API_KEY", "argilla.apikey")  # matches training/argilla-compose.yml's API_KEY

    import argilla as rg

    try:
        client = rg.Argilla(api_url=api_url, api_key=api_key)
        client.me  # cheap call that actually exercises the connection
    except Exception as exc:  # noqa: BLE001
        log.warning(
            "Argilla server unreachable at %s (%s) -- start one with "
            "`docker compose -f training/argilla-compose.yml up -d` (see module "
            "docstring) to actually push records. No records were sent.", api_url, exc,
        )
        return

    rows = read_jsonl(DATA_DIR / args.split)[: args.n]
    workspace = _ensure_workspace(client)
    dataset = build_dataset(client, args.dataset_name, workspace)
    n_pushed = push_records(dataset, rows)
    log.info(
        "pushed %d records with rule-teacher suggestions to Argilla dataset %r at %s -- "
        "human review is a separate, still-manual step (no legal expert available "
        "in this environment to perform it).",
        n_pushed, args.dataset_name, api_url,
    )


if __name__ == "__main__":
    main()
