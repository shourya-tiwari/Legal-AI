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
- **Base model**: fine-tuned **InLegalBERT** or **LegalBERT** (open-source, BERT-family models pretrained on legal corpora) with a token-classification head.
- **Zero-shot fallback**: **GLiNER** (open-source zero-shot NER) for entity types not covered by the fine-tuned model's label set, so new entity categories don't require a full retrain to support.
- **General-purpose scaffolding**: spaCy pipelines for tokenization, sentence boundaries, and as the integration framework tying the above together.

### 5. Coreference resolution
Resolves pronouns and role references ("it", "the Company", "either party") to their entities, using an open-source coreference model (e.g., `fastcoref`) as the default, with structured LLM-based coreference (via the Model Router's Tier 0/1 models) as a fallback for cases the statistical model handles poorly (long-range, cross-section references common in contracts).

### 6. Deontic modality tagging
Classifies each clause (or sub-clause) by its **deontic modality** — is it an obligation ("shall"), a permission ("may"), a prohibition ("shall not"), or discretionary ("in its sole discretion")? This is an established area of legal NLP research applied here as engineering, not a novel contribution in itself (see `NOVELTY.md` for where deontic tagging becomes an input to genuinely novel downstream analysis). Modeled as sequence tagging: initially bootstrapped via weak supervision (frontier-LLM labeling of a seed set), then distilled into a small, fast BERT-sized tagger for production latency/cost (`DEEP_LEARNING.md`).

### 7. Temporal expression normalization
Normalizes relative and absolute date/duration expressions ("within 30 days of the Effective Date", "on or before January 1, 2027") into machine-comparable representations, feeding both the Timeline feature (V1 lineage) and the Simulation Agent (`AGENTS.md`, `NOVELTY.md` #2).

### 8. Clause type classification
A learned classifier (extending V1's static risky-term list into a real taxonomy: indemnification, limitation of liability, termination, confidentiality, assignment, governing law, dispute resolution, force majeure, IP ownership, payment terms, etc.) — trained per `DEEP_LEARNING.md`, evaluated against **CUAD**'s labeled clause-type categories, which cover a materially overlapping taxonomy.

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

- **Clause type classification** and **NER** evaluated against **CUAD**'s labeled categories and span annotations.
- **Entailment/consistency tasks** (does this clause imply/contradict another) evaluated against **ContractNLI**.
- **Deontic tagging** evaluated via an internally curated gold set (no large public deontic-tagged legal corpus exists at the scale needed — bootstrapped and expanded via the active learning loop in `DEEP_LEARNING.md`).
- Target: inter-annotator agreement on the internal gold set tracked over time as the tagging model improves, not just a static accuracy number — legal text annotation genuinely has disagreement among human experts, and the eval should reflect that rather than assume ground truth is unambiguous.
