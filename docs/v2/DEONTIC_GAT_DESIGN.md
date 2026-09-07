# Deontic Graph Attention Network — architecture design (`NOVELTY.md` #1)

**Status: architecture design only.** This is the buildable half of
`docs/v2/TASKS.md`'s "Idea #1 (Deontic GAT conflict detection):
literature/patent search + architecture design (CPU); GNN training uses
Phase 6 GPU." The literature/patent search half is **not** done here —
that needs a qualified patent counsel search (ACL Anthology, JURIX, ICAIL
proceedings, and a formal patent search), not an AI-generated substitute,
and this document does not claim novelty has been confirmed. What follows
is a concrete, buildable architecture proposal so that (a) the GPU
training step has a real design to execute against once undertaken, and
(b) a future literature/patent search has a specific mechanism to check
prior art against, rather than only the one-paragraph sketch in
`NOVELTY.md`.

## What already exists to build on

- **Node data**: `app/services/kg/schema.py`'s shipped `Document`/`Clause`/
  `DefinedTerm`/`CrossReferenceTarget` nodes. `Clause` already carries
  `deontic_modalities: [str]` (obligation/permission/prohibition/discretion,
  `app/services/nlp/deontic.py`).
- **What's deliberately NOT modeled yet**: `Obligation` nodes with resolved
  actor/action, and `TRIGGERED_BY`/`OBLIGATES`/`CONFLICTS_WITH` edges
  (`docs/v2/KNOWLEDGE_GRAPH.md`'s full target schema, `kg/schema.py`'s own
  docstring). The deontic tagger doesn't resolve `actor` — a real
  `Obligation` node graph today would be guessing at who bears the
  obligation, not just what it says.
- **Existing candidate-conflict signal**: `kg/queries.py::find_potential_conflicts`
  — an exact-term-string match between an obligation clause and a
  prohibition clause sharing a defined term, across documents. This is the
  *rule-based floor* the GAT would need to learn to generalize past, and
  (see Training below) the cheapest available source of weak labels.
- **Legal-semantic embeddings**: `NOVELTY.md` #3's fingerprinting model
  (hard-negative pair construction done, `LEARNING_LOG.md` #49; the
  contrastive fine-tune itself is GPU-blocked) is the intended edge-feature
  input for "legal-semantic similarity of the governed action."

## Prerequisite: `Obligation` nodes, minimally scoped

The GAT needs graph nodes to attend over. Rather than the full target
schema's `Obligation(actor, action, ...)` (which needs actor resolution
this repo doesn't have), a **minimally-scoped** `Obligation` node is
buildable now:

```
Obligation
  id: STRING (doc:{id}:obligation:{clause_id}:{modality})
  clause_id: STRING (FK to Clause)
  modality: STRING (obligation | prohibition | permission | discretion)
  trigger_phrase: STRING (DeonticTag.trigger_phrase, e.g. "shall not")
  governed_action_text: STRING (the clause text itself, for embedding)
  # actor: deliberately OMITTED -- not resolved, would be guessing
```

One `Obligation` node per `DeonticTag` a clause carries (a clause with
both an obligation and a discretion tag yields two nodes). This is honest
about the actor gap rather than pretending to resolve it, and is a much
smaller schema change than the full target vision — buildable independent
of, and before, any GNN training.

## Graph construction

- **Nodes**: `Obligation` nodes as above, scoped per-org (all documents in
  a portfolio), mirroring `builder.py`'s existing per-org/per-document
  node-id scheme.
- **Candidate edges** (not all-pairs — that's O(n²) over a portfolio and
  mostly noise): an edge is proposed between two `Obligation` nodes when
  **either** (a) they share a defined term (`kg/queries.py`'s existing
  `find_clauses_using_term`/`SAME_AS` traversal already computes this), or
  (b) their governed-action embeddings (idea #3's fingerprint, once
  trained) are within a similarity threshold. This mirrors `hybrid.py`'s
  existing RRF pattern of combining a sparse/exact signal with a dense one,
  applied here to edge *proposal* rather than retrieval.
- **Edge features** (the GAT's attention mechanism weighs these):
  1. **Deontic modality compatibility** — a fixed 4×4 compatibility table
     (obligation vs. prohibition = high conflict potential; permission vs.
     permission = low), the same kind of small fixed lookup
     `risk_radar/rules.py`'s `RISK_CATEGORIES` uses elsewhere in this repo
     for a similar "small enumerable mapping" need.
  2. **Temporal overlap** — from `NLP.md`'s temporal-expression extraction,
     when both obligations have a resolved date/window; unresolved
     durations contribute no signal, honestly, matching `temporal.py`'s
     own refusal to guess.
  3. **Legal-semantic similarity** — cosine similarity of the two
     governed-action embeddings (idea #3's fingerprint model, once GPU
     training happens) or, until then, `RerankResult` scores from the
     existing Model Router `rerank` capability as a fallback.

## Model architecture

A standard 2-layer Graph Attention Network (Veličković et al.-style
architecture — the GAT mechanism itself is an established, off-the-shelf
building block, per `NOVELTY.md`'s own "established building blocks"
framing; nothing about the network layer itself is proposed as novel):

```
Input:  node embedding (governed_action_text via idea #3's fingerprint
        model, or the Class-A hashing embedder as an interim CPU-only
        input before GPU training is undertaken) concatenated with a
        one-hot modality vector.
Layer 1: multi-head GAT (4 heads), attending over candidate-edge neighbors,
         with edge features (above) fed as an additive attention bias, not
         just node features -- the specific mechanism NOVELTY.md #1 names
         as the proposed contribution (edges attend on deontic
         compatibility + temporal overlap + legal-semantic similarity
         jointly, not node similarity alone).
Layer 2: multi-head GAT (1 head), producing a final node embedding.
Output head: a 2-layer MLP over the concatenated pair of node embeddings
        for each candidate edge, producing a conflict-likelihood score
        in [0, 1].
```

## Training data and weak supervision

No hand-labeled conflict dataset exists. Following this repo's own
established weak-supervision precedent (`training/prepare_clause_data.py`'s
`--weak-corpus` step; `training/prepare_sensitivity_data.py`;
`training/prepare_risk_data.py`, `LEARNING_LOG.md` #43/#45): distill from
the *existing* rule-based `find_potential_conflicts` as the weak-label
source. A candidate pair is a **weak positive** if the rule-based check
already flags it as a candidate conflict; a **weak negative** is a
same-portfolio pair with no shared term and low embedding similarity. The
known ceiling this repo has already hit twice this session (`LEARNING_LOG.md`
#43, #45): a model trained purely on labels generated by an existing rule
can, at best, learn to reproduce that rule — the value of the GAT would
have to come from generalizing to conflicts the exact-term rule structurally
misses (different defined terms, paraphrased obligations), which is a
real but narrower opportunity than "the model learns something the rule
never encoded." Any real eval-gate promotion attempt should hold out a
small hand-labeled set (mirroring `SENSITIVITY_GOLD`/`RISK_SEVERITY_GOLD`'s
role) specifically containing paraphrase-conflict pairs the rule can't see,
so the evaluation actually tests the generalization claim rather than
being a near-tautology against the rule's own labels.

## What is genuinely GPU-blocked vs. buildable now

| Piece | Status |
|---|---|
| Minimally-scoped `Obligation` node + candidate-edge construction | Buildable now, CPU-only, no new node type beyond what's described above |
| Edge feature computation (modality table, temporal overlap, embedding similarity via the Class-A fallback) | Buildable now, CPU-only |
| Weak-label generation from `find_potential_conflicts` | Buildable now, CPU-only, same technique as `prepare_risk_data.py` |
| GAT training (the actual learned attention weights) | GPU-blocked — needs a real training loop, a GPU tensor library pass (PyTorch Geometric or DGL), and meaningful data volume |
| Real embedding fingerprints as node features (idea #3's contrastive model) | GPU-blocked (idea #3's own training step) — the Class-A hashing embedder is a CPU-only interim substitute, expected to underperform |
| Literature/patent search confirming novelty | Needs qualified patent counsel — not something this document or any AI-generated search substitutes for |

## Honest limitations of this design

- The `Obligation` node's missing `actor` field means the GAT cannot
  distinguish "Party A's obligation conflicts with Party A's own
  prohibition" from "...with Party B's prohibition" — a real semantic gap
  this design does not close, inherited directly from the NLP pipeline's
  own documented limitation.
- Candidate-edge proposal (rather than all-pairs) means the GAT can only
  ever be as good as the recall of its two proposal signals (shared term,
  embedding similarity) — a genuinely different-defined-term, low-similarity
  paraphrase would never even become a candidate edge, let alone get scored.
- This document was written without executing the literature/patent search
  `NOVELTY.md` names as a prerequisite before further investment or
  disclosure — treat this as a design sketch to have ready if/when that
  search clears, not as evidence the search has been done.
