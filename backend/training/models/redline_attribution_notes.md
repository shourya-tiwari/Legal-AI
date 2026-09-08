# Redline Attribution — `NOVELTY.md` idea #4, CPU-only prototype

`backend/training/redline_attribution.py` · `LEARNING_LOG.md` #57

## What this prototypes

**NOVELTY.md idea #4, "Adaptive Negotiation Playbook Learning from Redline
History"** — specifically the CPU-only step `docs/v2/TASKS.md` names:
*"counterfactual fingerprint-delta attribution (CPU); Redline Acceptance
Predictor — classical model first."*

The idea's core mechanism: don't diff two clause versions textually —
isolate *which semantic change* most plausibly drove an edit to be
accepted vs. rejected, by (a) decomposing the edit into atomic legal
changes, (b) measuring each change's contribution to the "legal-semantic
fingerprint" movement via counterfactual ablation, and (c) comparing that
against a background distribution of the same change type across a corpus
of proposed-but-unresolved edits. Feed the resulting features to a learned
per-org acceptance model.

## Two blockers, both real

1. **No redline history exists anywhere in this codebase.** Confirmed by
   `LEARNING_LOG.md` #51's audit before the Negotiation/Drafting agent: no
   redlining feature, no document version-pair history. So the
   `(before, after, outcome)` data is **synthetic** — real clause snippets
   from `app/eval/gold_set.py`, edited by the same NOVELTY.md-named
   perturbations `prepare_embedding_data.py` (#49) established (modal swap,
   negation, numeric shift) plus a jurisdiction swap (#51's own example),
   applied in both directions. The accepted/rejected label is **generated**
   from a hand-specified prior over (perturbation type, direction) — a
   deliberate generative stand-in, not a derived signal. Its ceiling is
   exactly #43/#45/#56's: a model learning from it recovers *this prior*,
   not real negotiation behaviour.

2. **idea #4's fingerprint is idea #3's contrastive embedding — GPU-blocked**
   (#49). This prototype substitutes the Model Router's current
   `embed_content` (Class-A hashing by default in this environment). The
   attribution *technique* is embedding-agnostic; it sharpens as the
   fingerprint sharpens. Same caveat `services/consistency.py` carries.

## Results

### Counterfactual fingerprint-delta attribution — works

All four single-change hand-modelled scenarios attribute the fingerprint
movement to the correct atomic change (the change is known *by
construction* — the redline was built by applying exactly that
perturbation):

| scenario | expected dominant | result |
|---|---|---|
| `shall` → `may` | `modal_swap` | PASS |
| `shall` → `shall not` | `negation` | PASS |
| `30 days` → `300 days` | `numeric_shift` | PASS |
| `California` → `Delaware` | `jurisdiction_swap` | PASS |
| no change (before == after) | *(none)* | PASS — no fabricated cause |

The **background distribution** places the example redline's `modal_swap`
marginal at the **96th percentile** of all observed modal-swap deltas —
i.e. "this is an unusually large modal change" — which is the comparison
NOVELTY.md #4 describes.

### The Class-A limitation, shown not hidden

Scenario 5 (a negation flip buried in heavy boilerplate rewording) is
marked **soft**: on the hashing embedder the reword dominates
(`other_reword` share 0.93 vs `negation` 0.07). This is the honest
demonstration of why idea #4 needs idea #3's *legal-effect* fingerprint —
a generic/lexical embedding cannot suppress boilerplate movement to let
the small-but-consequential legal change surface. The scenario is reported,
not asserted as a pass.

### Redline Acceptance Predictor (classical) — does NOT beat majority

| metric | value |
|---|---|
| n synthetic redlines | 116 (55 accepted / 61 rejected) |
| holdout accuracy | **0.514** |
| majority-class baseline | **0.514** |

**This negative result is precise and instructive.** The feature vector is
*unsigned* per-kind fingerprint-delta **magnitudes**. But acceptance in the
generative prior is **direction-dependent**: `shall→may` is accepted,
`may→shall` rejected, and the two edits have near-identical
`|fingerprint delta|`. A magnitude-only feature structurally cannot
separate them. Recovering direction needs the **signed** delta in idea
#3's *learned* fingerprint subspace (where "obligation added" and
"obligation removed" point opposite ways) — which is exactly the
dependency NOVELTY.md #4 states: idea #4 is built *on* idea #3's
fingerprint, not on a generic embedding. On the Class-A floor the
directional signal isn't there to learn from.

## What a real implementation would need

- **Real redline history** (a redlining/versioning feature that doesn't
  exist) — the synthetic prior is a scaffold for the pipeline, not a
  substitute for negotiation data.
- **idea #3's contrastive fingerprint** (GPU-blocked) — for the directional
  signal the acceptance predictor needs and the boilerplate-suppression
  the attribution needs.
- **Per-org isolation** — the Redline Acceptance Predictor is a per-org
  learned artifact (a customer-data derivative, `NOVELTY.md`'s
  trade-secret category), never pooled across orgs.

## Reproduce

```bash
cd backend && python training/redline_attribution.py          # full run + report
python training/redline_attribution.py --dry-run              # scenarios only
```

Writes `backend/training/models/redline_attribution_report.json` (committed
directly to git — small, human-readable, same convention as the other
`models/*_eval.json` / `*_report.json` files; DVC is for the binary
`*.joblib` artifacts only, per #54).
