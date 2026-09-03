# NLP Pipeline

V1's only "NLP" is a regex keyword scan over ~55 hardcoded risky terms (`services/risk_radar/rules.py`) and a naive paragraph splitter. There is no entity extraction, no coreference resolution, no understanding of what a clause actually *obligates* anyone to do. V2's NLP pipeline turns raw extracted text (from `COMPUTER_VISION.md`) into the structured `Clause` objects that every other subsystem — RAG, Knowledge Graph, agents — consumes.

## Pipeline stages

```
Raw text + layout hints (from CV pipeline)
  → 1. Clause/sentence segmentation
  → 2. Defined-term extraction & resolution
  → 3. Cross-reference resolution ("Section 4.2", "the Landlord")
  → 4. Named entity recognition (parties, dates, money, jurisdictions)
  → 5. Coreference resolution
  → 6. Deontic modality tagging (obligation / permission / prohibition / discretion)
  → 7. Temporal expression normalization
  → 8. Clause type classification (indemnification, termination, confidentiality, ...)
  → 9. Ambiguity/vagueness detection
  → Structured Clause object (canonical output)
```

### 1. Segmentation
Clause and sentence boundaries, using layout hints from the CV pipeline (numbered sections, indentation, heading structure) rather than pure regex on whitespace — a direct upgrade over V1's `\n\s*\n` paragraph split.

### 2. Defined-term extraction & resolution
Detects capitalized/quoted defined terms (`"Tenant"`, `"Effective Date"`) and their definitions, then resolves every subsequent use of that term back to its definition — a capability entirely absent from V1, and a prerequisite for catching defined-term inconsistency (a term used before it's defined, or defined twice inconsistently).

### 3. Cross-reference resolution
Resolves internal references ("as described in Section 4.2", "subject to Clause 9") into explicit links between clause objects — this is what the Knowledge Graph's `REFERENCES` edges are built from (`KNOWLEDGE_GRAPH.md`).

### 4. Named entity recognition (NER)
Domain-specific entity types: parties/roles, monetary amounts, dates/durations, jurisdictions, statute citations, defined terms.
- **Primary (configurable, no retrain)**: **GLiNER** (Apache-2.0 zero-shot NER) — one model, entity types specified at inference. Covers the full list above and lets new entity categories ship without a training run. This is the default (`MODEL_STACK.md`).
- **Fine-tuned head (accuracy on the fixed label set)**: a token-classification head on **InLegalBERT / Legal-BERT / ModernBERT** (BERT-family, legal-pretrained or current-best permissive encoder), trained per `DEEP_LEARNING.md` — used where GLiNER's zero-shot quality on a high-volume entity type isn't enough. Compared against GLiNER on eval before it becomes primary for that type, not assumed better.
- **Structured field extraction**: **NuExtract 2.0** (small template-driven model) for "fill this JSON schema from the clause" cases too fine-grained for a span model.
- **General-purpose scaffolding**: spaCy for tokenization, sentence boundaries, and as the integration framework.
- **CPU-only interim (shipped in Phase 2)**: regex for money/jurisdiction, defined-term extraction for parties — genuinely reliable for this domain.
- **Status (Phase 6):** GLiNER **shipped** as a Model Router capability (`ner` / `ner_extract` task, `providers/gliner_local.py`, Class B, optional `gliner` extra). `app/services/nlp/entities.py` merges GLiNER spans (party/date/duration/statute/jurisdiction) with the regex floor, fail-soft to regex-only. The fine-tuned token-classification head is **scaffolded, not trained** (`backend/training/`).

### 5. Coreference resolution
Resolves pronouns and role references ("it", "the Company", "either party") to their entities, using an open-source coreference model — **maverick-coref** as the default (better document-length context than `fastcoref`, still CPU-serveable), `fastcoref` as the fast fallback — with structured LLM-based coreference (a self-hosted Class A/B model via the Model Router) as an escalation for cases the statistical model handles poorly (long-range, cross-section references common in contracts). Phase 2 ships a clearly-labelled heuristic stand-in (`app/services/nlp/coref.py`); the real resolver (maverick-coref) is still a **Phase 6/8 follow-up** — not done.

### 6. Deontic modality tagging
Classifies each clause (or sub-clause) by its **deontic modality** — is it an obligation ("shall"), a permission ("may"), a prohibition ("shall not"), or discretionary ("in its sole discretion")? This is an established area of legal NLP research applied here as engineering, not a novel contribution in itself (see `NOVELTY.md` for where deontic tagging becomes an input to genuinely novel downstream analysis). Modeled as sequence tagging: initially bootstrapped via weak supervision (a **self-hosted teacher model** labelling a seed set — not a commercial API; `DEEP_LEARNING.md`), then distilled into a small, fast BERT-sized tagger for production latency/cost. Phase 2 ships a modal-verb regex Tier-0 tagger (eval-gated, 100% gold-set recall) that becomes the permanent fast pre-filter and the distillation bootstrap. **Status (Phase 6):** the weak-supervise-then-distil pipeline is **scaffolded** (`backend/training/prepare_deontic_data.py` — rule teacher, `--llm-teacher` for the Model-Router teacher; `train_deontic_tagger.py` — multi-label LoRA), not run.

### 7. Temporal expression normalization
Normalizes relative and absolute date/duration expressions ("within 30 days of the Effective Date", "on or before January 1, 2027") into machine-comparable representations, feeding both the Timeline feature (V1 lineage) and the Simulation Agent (`AGENTS.md`, `NOVELTY.md` #2).

### 8. Clause type classification
A learned classifier (extending V1's static risky-term list into a real taxonomy: indemnification, limitation of liability, termination, confidentiality, assignment, governing law, dispute resolution, force majeure, IP ownership, payment terms, etc.) — a fine-tuned head on a **ModernBERT / DeBERTa-v3 / Legal-BERT** base, trained per `DEEP_LEARNING.md`, evaluated against **CUAD**'s labeled clause-type categories. Phase 2 ships a keyword-taxonomy rule base + optional LLM escalation as the CPU-only interim, kept as a Tier-0 pre-filter once the learned model lands. **Status (Phase 6):** the fine-tune is **scaffolded** (`backend/training/prepare_clause_data.py` builds train data from LegalBench cuad_* + the gold set + rule weak-supervision; `train_clause_classifier.py` is LoRA on a ModernBERT/Legal-BERT base), not run — promotion is eval-gated against the rule baseline.

### 9. Ambiguity/vagueness detection
Flags clauses containing known vague standards ("best efforts," "reasonable efforts," "commercially reasonable," "material adverse change" — several of which V1's `rules.py` already lists as risky terms) and elevates them for the Risk & Compliance Agent, now with a learned confidence score rather than a flat keyword hit.

## Canonical output: the Clause object

```
ClauseObject {
  id, document_version_id, ordinal, text, page_ref, bbox (from CV pipeline)
  clause_type: enum
  deontic_tags: [{ span, modality: obligation|permission|prohibition|discretion, actor, action }]
  entities: [{ span, type, resolved_id }]
  defined_terms_used: [term_id, ...]
  cross_references: [clause_id, ...]
  temporal_expressions: [{ span, normalized_date_or_duration }]
  ambiguity_flags: [{ span, term, confidence }]
  embedding_ref: vector_id            # AI_STACK.md
  kg_node_id: node_id                 # KNOWLEDGE_GRAPH.md
}
```

This object is the single canonical unit that RAG chunking (`AI_STACK.md`), knowledge graph construction (`KNOWLEDGE_GRAPH.md`), and every agent (`AGENTS.md`) consume — replacing V1's untyped paragraph-block dicts (`{"id", "text", "type", "page"}`) with a structure rich enough to support the rest of V2.

## Evaluation

- Housed in the **Inspect AI** suite (`ARCHITECTURE.md`), CI-gated. **Status (Phase 6):** the graded harness is shipped — `app/eval/{datasets,metrics,tasks,cutover_gate}.py` + Inspect-AI wrappers + the `eval_runs` table. Loaders use **LegalBench** (`nguha/legalbench` cuad_*/contract_nli_* subtasks) + **MNLI**; the script-based CUAD-QA/ContractNLI datasets no longer load under `datasets` ≥ 3, so LegalBench's reformatted subtasks are the maintained path.
- **Clause type classification** and **deontic tagging** evaluated against the hand-curated gold set (fast CI gate, `run_eval.py`; no large public deontic-tagged legal corpus exists at the scale needed — bootstrapped and expanded via the active-learning loop in `DEEP_LEARNING.md`); **NER** and clause QA against LegalBench cuad_* subtasks.
- **Entailment/faithfulness** — the Verifier's NLI head (`verify_nli`) is graded on **MNLI** (0.91 acc) and on `FAITHFULNESS_GOLD` (8/8 vs the lexical stand-in's 6/8).
- Target: inter-annotator agreement on the internal gold set tracked over time as the tagging model improves, not just a static accuracy number — legal text annotation genuinely has disagreement among human experts, and the eval should reflect that rather than assume ground truth is unambiguous.
