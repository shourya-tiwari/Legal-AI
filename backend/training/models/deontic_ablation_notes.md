# Research note: Deontic-Structure-Aware Counterfactual Ablation (`NOVELTY.md` #5)

**Status: CPU-only prototype, done.** This validates the *ablation technique*
itself, not a production risk-explanation feature — nothing in `app/`
calls this. `training/deontic_ablation.py`, `LEARNING_LOG.md` #54.

## What this is

`NOVELTY.md` idea #5 proposes explaining a risk-score prediction by
perturbing **legally meaningful sub-spans** (a deontic modal marker, an
extracted entity, a defined term) one at a time, rather than generic
tokens/n-grams the way plain text-SHAP would. This reuses spans the
*existing* NLP pipeline already extracts (`DeonticTag.trigger_phrase`,
`EntityMention.text`, `ClauseObject.defined_terms_used`) — no new parser
was built for this — and runs each perturbed clause back through the
trained Risk Scoring Model (`train_risk_model.py`, #45) to measure the
shift in predicted-class probability.

This model was already documented as **not promoted** (`risk_model_card.md`
— it didn't beat the weak-supervision heuristic on `RISK_SEVERITY_GOLD`).
Using it here anyway is deliberate: idea #5 is about validating an
*attribution method*, and any trained classifier is a valid subject for
that — the ablation technique doesn't need a production-grade model to
demonstrate whether it produces legible, structurally-meaningful
explanations.

## What was found

Running the ablation against `RISK_SEVERITY_GOLD`'s first 5 examples
produced near-zero deltas for most spans (e.g. removing "shall" from
"The Contractor shall indemnify..." shifted the `high` prediction's
probability by `-0.0000`). Only `deontic_marker` spans ever fired for
these 5 examples — no `entity:*` or `defined_term` attributions appeared,
because none of these particular gold clauses contain a money amount, a
jurisdiction (the only two entity types the Class-A regex floor extracts
without `NER_ENABLED`), or a defined term.

A richer, separately-constructed test clause —
`'The Tenant ("Tenant") shall pay the Landlord a security deposit of
$5000 within 30 days.'` — confirmed all three span types work correctly
end to end: `deontic_marker` ("shall", delta `+0.9568`), `defined_term`
("Tenant", delta `-0.0001`), and `entity:money` ("$5000", delta `0.0`).

**The near-zero deltas on the actual gold set are themselves an
informative result, not a null one.** They're consistent with
`risk_model_card.md`'s own diagnosis of *why* this model failed its eval
gate: SHAP-based token analysis in that card already found the model
"latched onto superficial n-grams correlated with the heuristic's keyword
hits, not the underlying legal-risk concept." This ablation method arrives
at the same conclusion through a second, independent technique — removing
the actual deontic marker barely moves this model's prediction, meaning
its `high`/`medium`/`low` calls are not, in fact, substantially driven by
the modal-verb structure a legal reviewer would expect to matter. A
correctly-attributing model on well-separated examples should show large,
legible deltas concentrated on the deontic marker (as the $5000 example
does); a model that doesn't is a model whose explanations wouldn't survive
scrutiny even if its raw accuracy had been higher.

## Honest limitations

- Validated against one (not-promoted) classical model, not the eventual
  transformer-based clause/risk heads this repo's roadmap still has as
  GPU-blocked future work — the technique should be re-validated once a
  promoted model exists to explain.
- Only two entity types are ever available without `NER_ENABLED`+`gliner`
  installed (money, jurisdiction) — dates/durations/parties would need
  GLiNER escalation to appear as `entity:*` attributions.
- Single-instance-removal ablation (the first occurrence of a span) is the
  standard convention but doesn't capture interaction effects between two
  spans removed together.

## Next step

Formal literature/patent search (`NOVELTY.md`'s own stated next gate:
"structure-aware extensions of SHAP/LIME exist in other domains ...
adjacent structure-aware-explainability prior art is likely to exist and
must be checked") needs qualified patent counsel — genuinely blocked, not
something to do informally here.
