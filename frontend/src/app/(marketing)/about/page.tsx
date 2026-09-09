import Link from "next/link";
import { ArrowRight, ArrowUpRight } from "lucide-react";
import { GithubIcon } from "@/components/shared/brand-icons";
import { MarketingHero, Section, SectionTitle } from "@/components/marketing/section";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { FadeIn } from "@/components/marketing/fade-in";

export const metadata = {
  title: "About the project",
  description:
    "An engineering case study: how LegalAI evolved from a single-model Gemini demo into a self-hosted, provider-agnostic legal reasoning platform.",
};

const WHY = [
  {
    title: "Why it was built",
    body: "Contract review is high-stakes, repetitive, and full of text that a law firm or in-house team cannot send to a third-party API. The interesting version of this product isn't \"call a big model\" — it's \"get genuinely useful analysis while the privileged text never leaves the building.\" That constraint is the whole project.",
  },
  {
    title: "The vision",
    body: "A legal reasoning platform an organisation runs on its own hardware — laptop, single server, or air-gapped cluster — where the quality comes from structure, retrieval, a knowledge graph, fine-tuned classifiers, and a verifier that can say \"I'm not sure.\" An external API is allowed only where a cutover gate proves it wins, and only for documents whose tier permits it.",
  },
  {
    title: "Design philosophy",
    body: "Rule-based first, neural where it earns its place. Every degradation path is honest — the knowledge graph no-ops when Memgraph is down, the NLI head falls back to lexical overlap, generation raises a clear error rather than guessing. Nothing is auto-applied: redlines, overrides, and flagged analyses all route through a human.",
  },
];

const DECISIONS = [
  ["Provider-agnosticism is enforced, not intended", "No module outside the Model Router's provider package may import a vendor SDK — a CI-gated import-linter contract. Services name a task; the router picks the provider. This is what keeps the air-gapped build actually air-gapped."],
  ["Sensitivity is a first-class property", "Every document carries one of four tiers, assigned on upload. The Class-C gate keys on it, the router fails closed for confidential/privileged, and a PII redaction gate runs before any external dispatch. Before this existed, every call site passed \"internal\" implicitly and the gate protected nothing."],
  ["The verifier is the release gate", "Every agent summary and grounded answer is entailment-checked against its sources. A fabricated citation, a knowledge-graph conflict, or an unsupported claim sets needs_human_review and drops the run into a real queue."],
  ["Model choices are gated by evaluation", "A task routes to a self-hosted model by default only when a graded cutover gate shows it meets or beats the external baseline. \"We chose not to ship this model\" is a CI-enforced invariant with a model card explaining why."],
  ["Honest scope over impressive scope", "The classical sensitivity and risk classifiers were trained, evaluated, and not promoted because they lost to the rules. That result is documented in a model card rather than hidden."],
];

const RESEARCH = [
  ["Deontic graph attention", "Graph-attention networks over an obligation graph for cross-document conflict detection — inspired by the gap between string-match conflict detection and true semantic conflict."],
  ["Temporal obligation simulation", "Auto-deriving downstream dates from \"N days after <trigger>\" conditional patterns, distinct from absolute-date extraction."],
  ["Legal-semantic fingerprinting", "Contrastive clause embeddings trained on verified hard negatives — a modal-verb swap or a negation is textually tiny but legally opposite."],
  ["Adaptive negotiation playbooks", "Procedural memory of an organisation's negotiation history, beyond static preferences."],
  ["Deontic-structure-aware ablation", "Explaining a prediction by perturbing one legally-meaningful span at a time — a modal marker, an entity, a defined term."],
];

const TECH = [
  ["Backend", "FastAPI · Pydantic · SQLAlchemy · Postgres / SQLite · Redis"],
  ["AI orchestration", "LangGraph · DBOS durable execution · a declarative Model Router · import-linter"],
  ["Models", "Qwen3-8B/14B · bge-m3 + bge-reranker on TEI · DeBERTa NLI · GLiNER NER"],
  ["Retrieval & graph", "Hybrid RAG with RRF · rank-bm25 · FAISS · Memgraph / embedded KùzuDB"],
  ["NLP / CV", "regex-first pipeline · dateparser · PyMuPDF · OpenCV · Tesseract OCR fallback"],
  ["Frontend", "Next.js · TypeScript · Tailwind · TanStack Query · React Flow · Recharts"],
  ["Eval & training", "Inspect AI · LegalBench · MLflow · DVC · Argilla"],
  ["Observability & governance", "OpenTelemetry · SHA-256 egress audit trail · per-call routing logs · RBAC"],
];

const PHASES = [
  ["Phase 0–1", "V1 hardening, then a FastAPI re-platform: Postgres/Redis, org-scoped auth, document persistence, and the provider-agnostic Model Router seam."],
  ["Phase 2", "CPU NLP + CV pipelines turn flat text into a structured ClauseObject graph — segmentation, defined terms, deontic tagging, temporal normalisation, ambiguity detection."],
  ["Phase 3", "Knowledge Graph (Memgraph) + hybrid RAG (dense + sparse + graph, RRF fusion) replace a hardcoded knowledge base."],
  ["Phase 4", "A planner-driven LangGraph agent pipeline with a real NLI faithfulness verifier gating every summary."],
  ["Phase 5", "The Model Router becomes genuinely provider-agnostic: embeddings and reranking self-hosted, Gemini demoted to an optional Class C plugin, an import-linter contract enforcing the boundary."],
  ["Phase 6", "Self-hosted generation target (Qwen3-8B/14B), a graded eval harness with a cutover gate, GLiNER NER, the NLI head."],
  ["Phase 7", "Document sensitivity tiering enforced end-to-end, a PII redaction gate + egress audit trail, per-user identity + RBAC, on-prem/air-gapped packaging, a collapsed data layer (KùzuDB), durable execution (DBOS), a three-tier memory service, and the first Next.js SPA."],
  ["Phase 8", "Bitemporal graph versioning, cross-document consistency + simulation baselines, a negotiation drafting agent, the risk dashboard + knowledge-graph explorer, classical training runs (eval-gated, not promoted), MLflow + DVC, and five research prototypes from NOVELTY.md."],
];

const STATS = [
  ["8", "delivery phases, each deployable"],
  ["400+", "backend tests, green"],
  ["40+", "API endpoints, all typed"],
  ["4", "sensitivity tiers, enforced end-to-end"],
  ["3", "knowledge-graph / data-layer backends"],
  ["0", "model credentials required to run"],
];

const FUTURE = [
  {
    kind: "Next phase",
    tone: "outline" as const,
    items: [
      "Multi-tenant scale, SOC 2 and GDPR workflows",
      "Streaming agent trace over a session WebSocket",
      "Negotiation Studio — an interactive drafting surface",
      "Alembic migrations replacing the interim column shim",
    ],
  },
  {
    kind: "Pending stronger hardware (GPU)",
    tone: "warning" as const,
    items: [
      "Fine-tuned clause-type and deontic-tagger heads (pipeline verified via dry-run / smoke)",
      "The contrastive legal-clause embedding model (122 verified triplets built, CPU-side)",
      "Deontic-GAT training (architecture designed in DEONTIC_GAT_DESIGN.md)",
      "A transformer sensitivity classifier to beat the rules",
    ],
  },
  {
    kind: "Pending infrastructure or a human",
    tone: "info" as const,
    items: [
      "Legal-expert adjudication of weak labels (Argilla server runs; no expert in this environment)",
      "Formal prior-art / patent-counsel review of the five research directions",
      "Eval-gated promotion wired into CI to block a merge on a failed cutover gate",
    ],
  },
];

export default function AboutPage() {
  return (
    <>
      <MarketingHero
        eyebrow="Engineering case study"
        title="From a Gemini demo to a self-hosted legal reasoning platform"
        description="LegalAI started as a thin wrapper around one external model. It is now a provider-agnostic system where the domain quality comes from retrieval, a knowledge graph, fine-tuned heads, and a verifier — not from model scale — and where the deployment can run completely disconnected."
      >
        <div className="flex flex-wrap justify-center gap-3">
          <Button asChild>
            <Link href="/architecture">
              See the architecture <ArrowRight />
            </Link>
          </Button>
          <Button variant="secondary" asChild>
            <Link href="/research">Research contributions</Link>
          </Button>
          <Button variant="ghost" asChild>
            <a
              href="https://github.com/shourya-tiwari/Legal-AI"
              target="_blank"
              rel="noreferrer"
            >
              <GithubIcon /> Source
            </a>
          </Button>
        </div>
      </MarketingHero>

      {/* Why / vision / philosophy */}
      <Section>
        <div className="space-y-4">
          {WHY.map((w, i) => (
            <FadeIn key={w.title} delay={i * 0.05}>
              <div className="rounded-xl border border-border bg-surface p-6">
                <h2 className="text-sm font-semibold">{w.title}</h2>
                <p className="mt-2 text-sm text-muted-foreground">{w.body}</p>
              </div>
            </FadeIn>
          ))}
        </div>
      </Section>

      {/* Architecture decisions */}
      <Section className="border-t border-border">
        <SectionTitle subtitle="Five choices that shaped the system, and the problem each one solved.">
          Architecture decisions
        </SectionTitle>
        <div className="mt-10 space-y-3">
          {DECISIONS.map(([title, body], i) => (
            <FadeIn key={title} delay={i * 0.04}>
              <div className="grid gap-2 rounded-xl border border-border bg-surface p-5 sm:grid-cols-[220px_1fr]">
                <p className="text-sm font-semibold">{title}</p>
                <p className="text-sm text-muted-foreground">{body}</p>
              </div>
            </FadeIn>
          ))}
        </div>
      </Section>

      {/* Research inspiration */}
      <Section className="border-t border-border">
        <SectionTitle subtitle="Where the five novelty directions came from.">
          Research inspiration
        </SectionTitle>
        <div className="mt-10 grid gap-3 sm:grid-cols-2">
          {RESEARCH.map(([title, body], i) => (
            <FadeIn key={title} delay={i * 0.04}>
              <div className="h-full rounded-xl border border-border bg-surface p-5">
                <p className="text-sm font-semibold">{title}</p>
                <p className="mt-1 text-sm text-muted-foreground">{body}</p>
              </div>
            </FadeIn>
          ))}
        </div>
        <Link
          href="/research"
          className="mt-8 inline-flex items-center gap-1.5 text-sm font-medium text-primary hover:underline"
        >
          Full research notes <ArrowRight className="size-4" />
        </Link>
      </Section>

      {/* Technologies */}
      <Section className="border-t border-border">
        <SectionTitle subtitle="Everything self-hostable; nothing that phones home by default.">
          Technologies used
        </SectionTitle>
        <div className="mt-10 grid gap-4 sm:grid-cols-2">
          {TECH.map(([cat, tech]) => (
            <div
              key={cat}
              className="rounded-xl border border-border bg-surface p-5"
            >
              <p className="text-xs font-medium uppercase tracking-wider text-subtle-foreground">
                {cat}
              </p>
              <p className="mt-2 text-sm text-muted-foreground">{tech}</p>
            </div>
          ))}
        </div>
      </Section>

      {/* Development journey */}
      <Section className="border-t border-border">
        <SectionTitle subtitle="Eight phases, each one leaving the system deployable. Recorded in detail in a 60-plus-entry append-only engineering journal.">
          Development journey
        </SectionTitle>
        <div className="mt-10 space-y-6">
          {PHASES.map(([label, body], i) => (
            <FadeIn key={label} delay={i * 0.03}>
              <div className="flex gap-4">
                <div className="w-20 shrink-0 pt-0.5 text-sm font-semibold text-primary">
                  {label}
                </div>
                <p className="text-sm text-muted-foreground">{body}</p>
              </div>
            </FadeIn>
          ))}
        </div>
      </Section>

      {/* Statistics */}
      <Section className="border-t border-border">
        <SectionTitle>By the numbers</SectionTitle>
        <div className="mt-10 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
          {STATS.map(([v, l]) => (
            <div
              key={l}
              className="rounded-xl border border-border bg-surface p-4 text-center"
            >
              <p className="text-2xl font-semibold tracking-tight">{v}</p>
              <p className="mt-1 text-xs text-muted-foreground">{l}</p>
            </div>
          ))}
        </div>
      </Section>

      {/* Future work */}
      <Section className="border-t border-border">
        <SectionTitle subtitle="What isn't done is either the next phase or explicitly blocked — on a GPU or on a person. Neither is hidden.">
          Future work
        </SectionTitle>
        <div className="mt-10 grid gap-4 lg:grid-cols-3">
          {FUTURE.map((col) => (
            <div
              key={col.kind}
              className="rounded-xl border border-border bg-surface p-5"
            >
              <Badge variant={col.tone}>{col.kind}</Badge>
              <ul className="mt-4 space-y-2.5">
                {col.items.map((it) => (
                  <li key={it} className="text-sm text-muted-foreground">
                    {it}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </Section>

      {/* Through-line + CTA */}
      <Section className="border-t border-border">
        <div className="rounded-xl border border-border bg-surface p-6">
          <h2 className="text-sm font-semibold">The through-line</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            Every phase moved inference toward the organisation&rsquo;s own
            hardware and away from any external dependency. The bounded GPU
            reality — one 16&nbsp;GB card — forced the architecture to be honest:
            an 8–14&nbsp;B model plus strong retrieval and fine-tuned
            classifiers, with an external API kept only where a cutover gate
            proves it wins.
          </p>
        </div>
        <div className="mt-8 flex flex-wrap gap-3">
          <Button asChild>
            <Link href="/welcome">
              Try the platform <ArrowRight />
            </Link>
          </Button>
          <Button variant="secondary" asChild>
            <Link href="/about/developer">
              About the developer <ArrowUpRight />
            </Link>
          </Button>
        </div>
      </Section>
    </>
  );
}
