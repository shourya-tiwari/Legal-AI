# Novelty: Research Ideas with Potential Patent Value

## Read this section before anything else

This document proposes **5 research directions** that go beyond applying established AI techniques to the legal domain. For each idea, this document explicitly separates:

- **Established building blocks** — existing, published/known techniques the idea is built from. These are *not* claimed as novel.
- **Novel contribution** — the specific combination, mechanism, or objective that this document proposes as potentially original.

**Important caveats, stated plainly:**

1. **This is not a patentability opinion.** Nothing here has been validated against prior art. A proper freedom-to-operate and novelty search (patent literature, academic literature, and existing commercial products) by a qualified patent attorney is required before any claim of novelty can be relied upon.
2. **"Potentially novel" means "not identified as existing by this analysis," not "confirmed original."** The legal-AI and legal-tech space is active and fast-moving; it is plausible that some component of any idea below already exists in a patent filing, an academic paper, or a competitor's product that this analysis did not surface.
3. **None of this is legal advice about intellectual property.** Decisions about whether and how to pursue patent protection should involve qualified IP counsel.
4. **These are research proposals, not implemented systems.** Each would require a research/validation phase (prototyping, benchmarking against baselines, and — for any patent consideration — formal prior-art search) before being treated as a product feature, per `ROADMAP.md` Phase 8.

5. **All training and experimentation runs on self-hosted infrastructure** (the Phase 6 GPU stack: PyTorch + TRL + Unsloth, MLflow + DVC, Inspect AI — `DEEP_LEARNING.md`, `MODEL_STACK.md`). No idea here depends on a commercial model or API, for training *or* inference. Where an idea's pipeline mentions weak supervision or LLM assistance, the model is a self-hosted open-weight one. This is deliberate: a research contribution the field can reproduce without a specific vendor's API is both better science and a stronger basis for any IP claim, and it keeps every one of these features available in the on-prem and air-gapped profiles.

---

## 1. Deontic Graph Attention Network for Cross-Document Obligation Conflict Detection

**Problem**: A single contract's obligations can be checked for internal consistency, but real organizations operate under *portfolios* of interrelated contracts (a master agreement, its amendments, related vendor agreements) where a conflict emerges only when obligations from *different documents* are considered together — e.g., an indemnification cap in a master agreement contradicted by an uncapped indemnification clause in a later order form.

**Established building blocks**:
- Deontic logic representations of legal obligations (an established academic area in legal NLP/AI & law research).
- Graph Attention Networks (GATs) as a general architecture for learning over graph-structured data.
- Knowledge graphs for legal entity/relationship representation (used elsewhere in legal tech).

**Novel contribution proposed here**: applying a graph-attention architecture specifically over a **deontically-typed obligation graph spanning multiple documents in a portfolio**, where edge attention weights are learned to predict conflict likelihood between obligation nodes based on (a) deontic modality compatibility (obligation vs. prohibition on the same action/actor/condition), (b) temporal overlap, and (c) legal-semantic similarity of the governed action (via the embedding model in `DEEP_LEARNING.md`). The specific combination — cross-document scope, deontic-typed edges, and a learned attention mechanism trained to predict conflicts (rather than hand-written conflict rules) — is the proposed original contribution, not the individual components.

**How it would work**: obligations extracted per `NLP.md` become graph nodes (already modeled in `KNOWLEDGE_GRAPH.md`); a GAT is trained (using contract portfolios with known/labeled conflicts as supervision, bootstrapped via weak supervision per `DEEP_LEARNING.md`) to output a conflict-likelihood score per obligation pair, replacing brittle rule-based conflict detection with a learned, generalizable signal.

**Why potentially non-obvious**: existing contract-conflict-detection approaches in the literature and commercial tools this analysis is aware of largely operate within a single document or via simple rule matching; a learned, cross-document, deontic-attention-weighted approach is a more specific and (as far as this analysis can determine without a formal search) less-established combination.

**Prior art risk**: **Moderate-to-high.** Graph neural networks applied to legal document analysis are an active academic research area; a targeted literature search (ACL Anthology, JURIX, ICAIL proceedings) and patent search is required before assuming this is unclaimed.

---

## 2. Temporal Obligation Decay Simulation

**Problem**: Contract risk is often not static — it emerges at a future point in time (an auto-renewal that silently triggers, a notice period that collides with another contract's deadline). V1 and most contract-review tools report risk as of the current text; they don't project it forward.

**Established building blocks**:
- Discrete-event simulation (a long-established technique in operations research/computer science).
- Temporal/conditional expression extraction from text (an established NLP task).
- Bitemporal data modeling (an established database technique, used in `KNOWLEDGE_GRAPH.md`).

**Novel contribution proposed here**: a **discrete-event simulator that operates directly over an extracted obligation graph** (not a hand-built simulation model), where each `TRIGGERED_BY`/conditional relationship extracted by the NLP pipeline becomes a simulation rule, and the simulator advances a hypothetical calendar to surface *emergent* risk states — combinations of trigger events across multiple contracts in a portfolio that individually look benign but jointly create risk (e.g., two contracts' notice periods that, if both auto-renew, leave no valid window to terminate either). The novel piece is the **automatic construction of the simulation model from NLP-extracted conditional logic**, rather than the simulation technique itself.

**How it would work**: the Simulation Agent (`AGENTS.md`) walks the knowledge graph's `TRIGGERED_BY` edges and normalized temporal expressions (`NLP.md`), builds a discrete-event schedule, and advances it forward (deterministically for fixed dates, via Monte Carlo sampling for conditional/uncertain triggers) to produce a probability-weighted timeline of future risk states, surfaced in the Timeline UI module (`FRONTEND.md`).

**Why potentially non-obvious**: the combination of (a) NLP-extracted conditional obligation logic, (b) automatic simulation-model construction from that logic (rather than manual scenario modeling), and (c) portfolio-scope emergent-risk detection is a specific pipeline this analysis did not find a direct precedent for, though contract lifecycle management tools with renewal alerts are an established (much simpler) adjacent category.

**Prior art risk**: **Moderate.** Renewal-date alerting is a commodity feature in contract lifecycle management software; the specific claim to differentiate on would need to be the automatic simulation-model construction and multi-contract emergent-risk detection, not "the system tracks renewal dates," which is not novel.

---

## 3. Legal-Semantic Fingerprinting for Lexically-Dissimilar Contradiction Detection

**Problem**: Two clauses can be lexically very different but legally contradictory (e.g., one clause capping liability at "direct damages only" and another, in a different document, stating liability "shall not be limited in any respect") — or conversely, lexically similar but legally distinct. Generic semantic similarity embeddings (trained for topical similarity) are not designed to distinguish these cases.

**Established building blocks**:
- Contrastive learning for sentence/passage embeddings (an established technique, e.g., SimCSE, sentence-transformers training methodology).
- Cross-encoder-based natural language inference (entailment/contradiction classification) as an established NLP task (used for the faithfulness checker in `AGENTS.md`).

**Novel contribution proposed here**: a **contrastive training objective specifically for "legal function equivalence/contradiction"** rather than generic semantic similarity — training pairs are constructed as (a) positive pairs: clauses with different wording but the same legal effect, and (b) hard-negative pairs: clauses with *similar* wording but different or contradictory legal effect (e.g., differing only in a negation, a cap amount, or a modal verb — "shall" vs. "may"). The resulting embedding space is proposed to be specifically discriminative on legal-effect axes that generic embedding models conflate, producing a "legal fingerprint" vector usable for fast, portfolio-scale contradiction search (approximate nearest-neighbor search for fingerprint *dissimilarity in a targeted subspace*, rather than standard similarity search) — this specific training-data construction strategy (mining near-miss negatives that differ minimally but legally significantly) and its application to contradiction search at scale is the proposed original contribution.

**Why potentially non-obvious**: general-purpose sentence embeddings and even domain-tuned legal embeddings (e.g., existing legal-BERT variants) are typically trained for topical/semantic similarity, not specifically for the "similar wording, opposite legal effect" discrimination this idea targets; the hard-negative mining strategy built around modal-verb/negation/numeric-threshold perturbations is a specific, targeted training methodology.

**Prior art risk**: **Moderate.** Contrastive fine-tuning of domain embeddings is common practice generally; the specific application to legal contradiction (as opposed to legal topic/similarity) search, and the specific hard-negative construction strategy, is the narrower claim that would need prior-art validation.

---

## 4. Adaptive Negotiation Playbook Learning from Redline History

**Problem**: Every organization has an implicit negotiation "style" — how far they'll move on liability caps, what payment terms they accept, which clauses they never compromise on — encoded only in the tribal knowledge of their legal team and the history of past redlines. No system today learns this automatically to assist future negotiations.

**Established building blocks**:
- Preference learning / learning-to-rank from historical human decisions (an established ML paradigm).
- Text diffing (an established, simple technique).
- Procedural memory as a concept in cognitive-architecture-inspired AI agent design (an established idea in the broader agentic-AI literature).

**Novel contribution proposed here**: a **"counterfactual redline diffing" method** that doesn't just diff two document versions textually, but isolates *which semantic change* (via the legal-semantic fingerprint of idea #3) most plausibly caused an edit to be accepted vs. rejected, by comparing the fingerprint delta of accepted edits against a background distribution of fingerprint deltas from a broader corpus of proposed-but-unresolved edits — effectively an ablation-style attribution method for negotiation outcomes, feeding a learned per-org policy model (the Redline Acceptance Predictor, `DEEP_LEARNING.md`) that then drives the Negotiation/Drafting Agent's default suggestions (`AGENTS.md`). The specific mechanism — counterfactual fingerprint-delta attribution as the *feature extraction step* for a negotiation-preference model — is the proposed original contribution, not "learn from past negotiations" in general, which is a known aspiration in contract-tech.

**Why potentially non-obvious**: several commercial contract-lifecycle-management tools already offer "clause libraries" and basic redline tracking; the specific technique of using fingerprint-delta counterfactual attribution to infer *why* an edit was accepted (rather than simply logging *that* it was accepted) is a more specific mechanism this analysis did not find precedent for, though the general goal of learning negotiation preferences from history is a known market direction.

**Prior art risk**: **High.** "Learn from your negotiation history" is a stated goal of multiple existing commercial CLM/negotiation-assist products; the defensible claim, if any, would need to rest narrowly on the counterfactual fingerprint-attribution mechanism specifically, not the general goal.

---

## 5. Explainable Risk Attribution via Deontic-Structure-Aware Counterfactual Ablation

**Problem**: A risk score (V1's simple keyword hit, or V2's learned `Risk Scoring Model`, `DEEP_LEARNING.md`) tells a user *that* a clause is risky but not, precisely, *which phrase* within the clause drives that score — a real gap for legal defensibility, where "the model said so" is not an acceptable explanation to a reviewing attorney.

**Established building blocks**:
- SHAP and other perturbation-based feature attribution methods (well-established in interpretable ML).
- Constituency/dependency parsing and clause-structure analysis (established NLP techniques).

**Novel contribution proposed here**: a **perturbation strategy for text ablation that respects deontic clause structure** rather than ablating arbitrary tokens or n-grams (as generic SHAP-for-text implementations typically do) — perturbations are generated by systematically removing or substituting specific deontic-tagged spans (the actor, the action, the modal/deontic marker, the condition, the deadline — from `NLP.md`'s tagging) one at a time, measuring the resulting shift in the Risk Scoring Model's output, and attributing risk contribution to *legally meaningful sub-spans* (e.g., "the risk contribution is concentrated in the modal marker 'shall not be limited', not in the surrounding boilerplate") rather than arbitrary token spans that may not align with anything a human reviewer would find meaningful. The novel piece is **using the deontic parse itself as the perturbation unit** for attribution, rather than generic tokens/n-grams.

**Why potentially non-obvious**: generic text-SHAP implementations ablate at the token or sentence level, which frequently produces attributions that don't align with legally meaningful structure; grounding the ablation units in a deontic parse specifically for legal-domain explainability is a targeted, domain-specific refinement of an established general method.

**Prior art risk**: **Low-to-moderate.** Structure-aware extensions of SHAP/LIME exist in other domains (e.g., syntax-aware NLP explainability research); the specific application using a *deontic* (rather than syntactic) parse as the ablation unit, for legal risk-score explanation specifically, is the narrower and more plausibly original claim — but adjacent structure-aware-explainability prior art is likely to exist and must be checked.

---

## Summary table

| # | Idea | Core novel mechanism | Prior-art risk (this analysis's rough estimate) |
|---|---|---|---|
| 1 | Deontic Graph Attention Conflict Detection | Learned attention over cross-document, deontically-typed obligation graph | Moderate–High |
| 2 | Temporal Obligation Decay Simulation | Auto-constructed discrete-event simulation from NLP-extracted conditional logic | Moderate |
| 3 | Legal-Semantic Fingerprinting | Contrastive embedding trained on legal-effect equivalence with targeted hard-negative mining | Moderate |
| 4 | Adaptive Negotiation Playbook Learning | Counterfactual fingerprint-delta attribution for redline acceptance | High |
| 5 | Deontic-Structure-Aware Counterfactual Ablation | Deontic parse as the SHAP-style perturbation unit | Low–Moderate |

**Next step for any of these**: before committing engineering time beyond a research prototype, commission a formal prior-art search (patent databases + ACL/JURIX/ICAIL academic literature + a competitive product survey) through qualified patent counsel. This document is a starting hypothesis for that search, not a substitute for it.

---

## Publication strategy

The open-source-first architecture makes several of these ideas *more* publishable, not less — a method that reproduces on open weights and open datasets is what venues and reviewers want. Candidate venues, roughly by fit:

| Idea | Primary venue candidates | Contribution shape |
|---|---|---|
| #1 Deontic GAT conflict detection | **NLLP workshop @ EMNLP/ACL**, **JURIX**, **ICAIL**; ML side → a GNN workshop | Method paper + a released cross-document-conflict benchmark (there is no good public one — building it is itself a contribution) |
| #2 Temporal obligation simulation | **JURIX**, **ICAIL**, **AI & Law journal** | System/method paper: auto-construction of a discrete-event model from extracted conditional logic; evaluated against hand-modelled scenarios |
| #3 Legal-semantic fingerprinting | **NLLP**, ***SEM / *ACL findings**, **SIGIR** (retrieval framing) | Embedding-method paper + released model + a "similar wording, opposite legal effect" evaluation set |
| #4 Adaptive negotiation playbook | **ICAIL**, **AI & Law**; possibly a preference-learning workshop | Method paper on counterfactual fingerprint-delta attribution; hardest to publish without proprietary redline data — a synthetic or partner-contributed dataset is the enabler |
| #5 Deontic-structure-aware ablation | **BlackboxNLP @ EMNLP** (interpretability), **NLLP**, **FAccT** (explainability-for-law framing) | Interpretability-method paper; the deontic-parse-as-perturbation-unit idea generalizes beyond risk scoring |

**Benchmark contributions are the highest-leverage output.** The legal-NLP field is short on good public evaluation data for exactly the cross-document, deontic, and contradiction tasks V2 targets. A well-constructed released benchmark (even without a novel model) is citable, defensible, community-building, and doubles as our own regression eval (`ARCHITECTURE.md`). Prioritize: (a) a cross-document obligation-conflict set (#1), (b) a legal-effect-equivalence / near-miss-contradiction set (#3).

**Reproducibility bar for any submission**: model weights or training code released, dataset released or synthesizable, exact dataset snapshot pinned via DVC, eval harness (Inspect AI) published, seeds fixed. This is already the internal engineering standard (`OVERVIEW.md` principle 7) — a publication is a side effect of doing it, not extra work.

## Patent vs. defensive-publication strategy

Patent and publication are in tension (a public disclosure can start or blow a filing clock). Decide per idea, with counsel, *before* disclosure:

- **File-first candidates**: ideas where the novel mechanism is a specific, describable technique with commercial defensibility and moderate-or-lower prior-art risk — currently **#5** (low–moderate risk) and possibly **#1**'s specific cross-document deontic-attention formulation. For these, a provisional filing precedes any paper, and the paper follows within the priority year.
- **Defensive-publication candidates**: ideas where prior-art risk is high (**#4**), or where the value is in the released benchmark/model rather than an enforceable claim. Publish deliberately to establish prior art and prevent a competitor from patenting around us, and compete on execution and data-network-effects instead.
- **Trade-secret candidates**: per-org learned artifacts (the Redline Acceptance Predictor's weights, an org's negotiation policy) are not patent or paper material — they are customer data derivatives, kept confidential and org-isolated by construction (`DEEP_LEARNING.md`).

**Open-source posture for the research track:** the *methods* and *benchmarks* are candidates for release (they build credibility and a hiring pipeline, and cost us little — the moat is the integrated product, the data, and the deployment story, not any single model). The *product* — the integrated agent graph, the routing policy, the corpus, the deployment tooling — is the commercial asset. This split should be explicit in every research decision: "would open-sourcing this specific thing help the field and cost us little, or is it load-bearing for the product?"

## What is *not* claimed as novel

To keep this document honest: the overall V2 architecture — provider-agnostic routing, hybrid RAG, a legal knowledge graph, multi-agent orchestration with a verifier, self-hosted open-weight inference — is **good engineering, not novel research**. Every piece exists in the literature or in practice. The contribution, if any, is in the five specific mechanisms above and in the integrated system's execution. Marketing that blurs this line damages credibility with exactly the technical and legal audiences the product needs to win.
