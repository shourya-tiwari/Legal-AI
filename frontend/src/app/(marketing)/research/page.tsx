import { Badge } from "@/components/ui/badge";
import { MarketingHero, Section } from "@/components/marketing/section";

export const metadata = {
  title: "Research",
  description:
    "Five research directions with potential patent value, each independently gated. CPU-only prototypes are done; GPU training and formal prior-art searches are the open work.",
};

const IDEAS = [
  {
    n: 1,
    title: "Deontic Graph Attention Network for cross-document obligation conflict detection",
    status: "Architecture design done",
    body: "A GAT over a minimally-scoped Obligation node graph, with a 3-feature edge-attention scheme (modality compatibility, temporal overlap, legal-semantic similarity) and a weak-supervision plan distilling the existing rule-based conflict finder. The literature/patent search and GNN training remain open.",
  },
  {
    n: 2,
    title: "Temporal obligation decay simulation",
    status: "CPU prototype validated",
    body: "Extracts “N days/months after <trigger phrase>” conditional patterns — distinct from absolute-date extraction — and, given hand-provided anchor dates, auto-derives downstream dates. Validated against five hand-modelled scenarios. The full portfolio TRIGGERED_BY-graph + Monte-Carlo version needs KG-schema growth.",
  },
  {
    n: 3,
    title: "Legal-semantic fingerprinting for lexically-dissimilar contradiction detection",
    status: "Hard-negative data done; contrastive fine-tune GPU-blocked",
    body: "122 verified (anchor, positive, hard-negative) triplets built with named perturbations — modal-verb swap, negation, day-count/dollar/percentage shift — each confirmed to actually change legal effect. The contrastive embedding fine-tune is the GPU-blocked step.",
  },
  {
    n: 4,
    title: "Adaptive negotiation playbook learning from redline history",
    status: "Prototype: a precise negative result",
    body: "A counterfactual fingerprint-delta attribution method plus a classical acceptance predictor. The predictor does not beat its majority baseline — a precise finding: unsigned delta magnitude can't encode edit direction, which needs idea #3's signed learned subspace. Blocked further on real redline history that doesn't exist yet.",
  },
  {
    n: 5,
    title: "Explainable risk attribution via deontic-structure-aware counterfactual ablation",
    status: "CPU prototype validated",
    body: "Perturbs one legally-meaningful span at a time — a deontic marker, an entity, a defined term — and measures the shift in predicted-class probability. Found near-zero attribution to the deontic marker on the real gold set, independently corroborating a SHAP-based finding that the trained risk model learned superficial n-grams, not legal structure.",
  },
];

export default function ResearchPage() {
  return (
    <>
      <MarketingHero
        eyebrow="Research track"
        title="Five ideas, each independently gated"
        description="Every idea gets a prototype and a benchmark before further investment. CPU-only components proceed anytime; GPU training and formal prior-art searches are the honest blockers."
      />
      <Section>
        <div className="space-y-6">
          {IDEAS.map((idea) => (
            <div
              key={idea.n}
              className="rounded-xl border border-border bg-surface p-6"
            >
              <div className="flex flex-wrap items-center gap-3">
                <span className="flex size-7 items-center justify-center rounded-lg bg-primary-muted text-sm font-semibold text-primary">
                  {idea.n}
                </span>
                <h3 className="flex-1 text-base font-semibold">{idea.title}</h3>
                <Badge variant="outline">{idea.status}</Badge>
              </div>
              <p className="mt-3 text-sm text-muted-foreground">{idea.body}</p>
            </div>
          ))}
        </div>
        <p className="mt-8 text-center text-xs text-subtle-foreground">
          The formal literature and patent searches require qualified patent
          counsel and are not attempted here.
        </p>
      </Section>
    </>
  );
}
