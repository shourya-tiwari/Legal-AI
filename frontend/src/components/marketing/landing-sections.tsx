import * as React from "react";
import Link from "next/link";
import {
  Upload,
  ShieldCheck,
  ScanSearch,
  Workflow,
  Sparkles,
  ArrowRight,
  ArrowUpRight,
  Network,
  GitCompareArrows,
  FlaskConical,
  Microscope,
  Layers,
  Cpu,
  Database,
  CircleCheckBig,
  GitBranch,
  Clock,
  BookOpen,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { GithubIcon } from "@/components/shared/brand-icons";
import { BrowserFrame } from "./browser-frame";
import { FadeIn } from "./fade-in";

/* ------------------------------------------------------------------ *
 * shared shell
 * ------------------------------------------------------------------ */
function SectionShell({
  id,
  alt,
  eyebrow,
  title,
  intro,
  children,
}: {
  id?: string;
  alt?: boolean;
  eyebrow: string;
  title: string;
  intro?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <section
      id={id}
      className={alt ? "border-y border-border bg-surface/40" : undefined}
    >
      <div className="mx-auto w-full max-w-6xl px-4 py-20 sm:px-6">
        <FadeIn>
          <p className="text-sm font-medium text-primary">{eyebrow}</p>
          <h2 className="mt-2 max-w-2xl text-2xl font-semibold tracking-tight sm:text-3xl">
            {title}
          </h2>
          {intro && (
            <p className="mt-3 max-w-2xl text-muted-foreground">{intro}</p>
          )}
        </FadeIn>
        <div className="mt-10">{children}</div>
      </div>
    </section>
  );
}

function FeatureRow({
  icon: Icon,
  title,
  body,
}: {
  icon: React.ElementType;
  title: string;
  body: string;
}) {
  return (
    <div className="flex gap-3 rounded-xl border border-border bg-surface p-5">
      <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-primary-muted text-primary">
        <Icon className="size-4" />
      </div>
      <div>
        <p className="text-sm font-semibold">{title}</p>
        <p className="mt-1 text-sm text-muted-foreground">{body}</p>
      </div>
    </div>
  );
}

function MoreLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <Link
      href={href}
      className="mt-8 inline-flex items-center gap-1.5 text-sm font-medium text-primary hover:underline"
    >
      {children} <ArrowRight className="size-4" />
    </Link>
  );
}

/* ------------------------------------------------------------------ *
 * How it works
 * ------------------------------------------------------------------ */
const STAGES = [
  {
    icon: Upload,
    title: "Upload",
    body: "PDF, DOCX, TXT, or a scanned image. Extraction is fully local — PyMuPDF, python-docx, and Tesseract OCR fallback. No cloud Document AI.",
  },
  {
    icon: ShieldCheck,
    title: "Classify",
    body: "A rule-based classifier assigns one of four sensitivity tiers. The tier is what the Model Router's Class-C gate keys on for the rest of the document's life.",
  },
  {
    icon: ScanSearch,
    title: "Extract",
    body: "Segmentation → typed ClauseObjects: deontic modality, defined terms, cross-references, entities, temporal expressions, ambiguity flags. Rule-first, GLiNER where enabled.",
  },
  {
    icon: Workflow,
    title: "Analyse",
    body: "A planner decides which agents to run. Risk radar, timeline, knowledge-graph conflict checks, negotiation redlines, cross-document consistency — only what the document needs.",
  },
  {
    icon: Sparkles,
    title: "Verify",
    body: "Every generated summary and answer is entailment-checked against its sources by an NLI head. Contradicted or unsupported claims are surfaced, and can route the run to a human.",
  },
];

export function LandingHowItWorks() {
  return (
    <SectionShell
      id="how-it-works"
      eyebrow="How it works"
      title="Upload to verified result, in five stages"
      intro="Each stage is a live endpoint with an honest degradation path when a dependency isn't reachable — the knowledge graph no-ops, the NLI head falls back to lexical overlap, generation raises a clear error."
    >
      <ol className="grid gap-4 md:grid-cols-3 lg:grid-cols-5">
        {STAGES.map((s, i) => (
          <FadeIn key={s.title} delay={i * 0.05}>
            <li className="flex h-full flex-col rounded-xl border border-border bg-surface p-5">
              <div className="flex items-center gap-2">
                <span className="flex size-6 items-center justify-center rounded-full bg-primary-muted text-xs font-semibold text-primary">
                  {i + 1}
                </span>
                <s.icon className="size-4 text-subtle-foreground" />
              </div>
              <p className="mt-3 text-sm font-semibold">{s.title}</p>
              <p className="mt-1 text-xs text-muted-foreground">{s.body}</p>
            </li>
          </FadeIn>
        ))}
      </ol>
    </SectionShell>
  );
}

/* ------------------------------------------------------------------ *
 * Architecture overview
 * ------------------------------------------------------------------ */
const LAYERS = [
  { icon: Layers, name: "Client", body: "A client-rendered Next.js SPA against a separate FastAPI origin. Auth optional." },
  { icon: ShieldCheck, name: "API", body: "Thin route → service modules, every route behind one guard: auth, rate limit, audit." },
  { icon: Cpu, name: "Model Router", body: "Every AI call names a task, never a model. Class A/B/C providers, self-hosted-first chains, an import-linter contract." },
  { icon: ScanSearch, name: "Pipelines", body: "Rule-first NLP + CV turn flat text into a structured ClauseObject graph." },
  { icon: Workflow, name: "Agents", body: "A planner-driven LangGraph: extraction → planner → dispatch → verifier. DBOS durable execution optional." },
  { icon: Network, name: "Knowledge & retrieval", body: "Memgraph or embedded KùzuDB, plus hybrid RAG — dense + sparse + graph fused by RRF." },
  { icon: Database, name: "Data", body: "Postgres or SQLite, Redis, content-addressed blobs. Documents, audit log, traces, eval runs." },
];

export function LandingArchitecture() {
  return (
    <SectionShell
      alt
      eyebrow="Architecture overview"
      title="Seven layers, each replaceable without touching the others"
      intro="Self-hosting is the spine, not a top-up. The domain quality comes from retrieval, the knowledge graph, fine-tuned heads, and the verifier — not from model scale."
    >
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {LAYERS.map((l, i) => (
          <FadeIn key={l.name} delay={i * 0.04}>
            <div className="flex h-full gap-3 rounded-xl border border-border bg-surface p-5">
              <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-elevated text-foreground">
                <l.icon className="size-4" />
              </div>
              <div>
                <p className="text-sm font-semibold">{l.name}</p>
                <p className="mt-1 text-sm text-muted-foreground">{l.body}</p>
              </div>
            </div>
          </FadeIn>
        ))}
      </div>
      <MoreLink href="/architecture">See the full architecture</MoreLink>
    </SectionShell>
  );
}

/* ------------------------------------------------------------------ *
 * AI pipeline
 * ------------------------------------------------------------------ */
const AGENT_NODES = [
  { name: "extraction", body: "Builds the ClauseObject graph — always runs." },
  { name: "planner", body: "Rule heuristics or an LLM plan pick the node set. Falls back to rules on any error." },
  { name: "risk / compliance", body: "Keyword sweep + KG conflict lookup for every defined term used." },
  { name: "research", body: "Hybrid RAG, but only for clauses already flagged by risk or ambiguity." },
  { name: "summary", body: "The one generating node — asks the model to cite retrieved sources by [N]." },
  { name: "verifier", body: "Citation validity + KG conflicts + real NLI faithfulness. The mandatory release gate." },
];

export function LandingAiPipeline() {
  return (
    <SectionShell
      eyebrow="AI pipeline"
      title="A pipeline that decides what to do, then checks its own work"
      intro="A document with no risk or ambiguity signal runs just extraction → planner → verifier. The verifier can fail the run: a fabricated citation, a KG conflict, or an unsupported claim sets needs_human_review and drops it into the review queue."
    >
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {AGENT_NODES.map((n, i) => (
          <FadeIn key={n.name} delay={i * 0.04}>
            <div className="h-full rounded-xl border border-border bg-surface p-5">
              <div className="flex items-center gap-2">
                <span className="font-mono text-xs text-primary">
                  {String(i + 1).padStart(2, "0")}
                </span>
                <p className="font-mono text-sm font-semibold">{n.name}</p>
              </div>
              <p className="mt-2 text-sm text-muted-foreground">{n.body}</p>
            </div>
          </FadeIn>
        ))}
      </div>
      <MoreLink href="/features">Every capability, mapped</MoreLink>
    </SectionShell>
  );
}

/* ------------------------------------------------------------------ *
 * Knowledge graph
 * ------------------------------------------------------------------ */
export function LandingKnowledgeGraph() {
  return (
    <SectionShell
      alt
      eyebrow="Knowledge graph"
      title="Your portfolio as a graph, not a folder of PDFs"
      intro="Defined terms are extracted per document, then linked across the portfolio only when both the alias text and the defining context match. Candidate cross-document conflicts surface obligation/prohibition pairs that share a term."
    >
      <div className="grid gap-6 lg:grid-cols-2 lg:items-center">
        <div className="space-y-3">
          {[
            { icon: Network, title: "Per-document terms, portfolio links", body: '"the Company" in two unrelated contracts is not auto-merged — linking needs matching context, not just matching text.' },
            { icon: GitCompareArrows, title: "Candidate conflicts", body: "Cross-document obligation vs. prohibition on a shared term — flagged for review, never asserted as a confirmed conflict." },
            { icon: Clock, title: "Bitemporal versioning", body: "Transaction time and valid time on every Document/Clause node. Ask what a term meant as of a past date." },
            { icon: Database, title: "Two backends", body: "Memgraph over Bolt, or an embedded KùzuDB with no server at all — the single-binary profile." },
          ].map((f) => (
            <FeatureRow key={f.title} {...f} />
          ))}
        </div>
        <FadeIn delay={0.1}>
          <BrowserFrame url="legalai.app/knowledge-graph">
            <div className="space-y-2 text-xs">
              <div className="flex items-center justify-between">
                <span className="font-medium">Term: &ldquo;Confidential Information&rdquo;</span>
                <Badge variant="outline">4 documents</Badge>
              </div>
              {[
                ["NDA — Northwind ↔ Cedar & Vale", "obligation", "success"],
                ["MSA — Northwind ↔ Bright Labs", "obligation", "success"],
                ["Vendor DPA — Northwind ↔ Cirroware", "prohibition", "warning"],
              ].map(([doc, kind, tone]) => (
                <div
                  key={doc}
                  className="flex items-center justify-between rounded-md border border-border bg-elevated px-3 py-2"
                >
                  <span className="text-muted-foreground">{doc}</span>
                  <Badge variant={tone as "success" | "warning"}>{kind}</Badge>
                </div>
              ))}
              <div className="flex items-center gap-1.5 pt-1 text-warning">
                <GitBranch className="size-3.5" />
                1 candidate cross-document conflict
              </div>
            </div>
          </BrowserFrame>
        </FadeIn>
      </div>
      <MoreLink href="/knowledge-graph">Open the graph explorer</MoreLink>
    </SectionShell>
  );
}

/* ------------------------------------------------------------------ *
 * Risk analysis
 * ------------------------------------------------------------------ */
const RISK_CATEGORIES = [
  "Liability & indemnity",
  "Termination",
  "Payment & financial",
  "IP & confidentiality",
  "Dispute resolution",
  "Compliance & regulatory",
  "Data & privacy",
  "Operational & delivery",
];

export function LandingRiskAnalysis() {
  return (
    <SectionShell
      eyebrow="Risk analysis"
      title="Eight categories, keyword and contextual, drill-down to the clause"
      intro="A rule-based keyword sweep is the always-on floor; an AI pass adds contextual detection. Results aggregate into a spider chart on the Risk Dashboard, and every point drills into the exact clauses that drove it."
    >
      <div className="grid gap-6 lg:grid-cols-2 lg:items-center">
        <div className="flex flex-wrap gap-2">
          {RISK_CATEGORIES.map((c) => (
            <span
              key={c}
              className="rounded-full border border-border bg-surface px-3 py-1.5 text-sm text-muted-foreground"
            >
              {c}
            </span>
          ))}
        </div>
        <FadeIn delay={0.1}>
          <BrowserFrame url="legalai.app/documents/1/risk">
            <div className="space-y-2.5 text-xs">
              {(
                [
                  ["Liability & indemnity", 92, "bg-danger"],
                  ["Termination", 68, "bg-warning"],
                  ["IP & confidentiality", 44, "bg-warning"],
                  ["Payment & financial", 21, "bg-success"],
                ] as const
              ).map(([label, val, barClass]) => (
                <div key={label}>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">{label}</span>
                    <span className="font-mono">{val}</span>
                  </div>
                  <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-elevated">
                    <div
                      className={`h-full rounded-full ${barClass}`}
                      style={{ width: `${val}%` }}
                    />
                  </div>
                </div>
              ))}
              <p className="pt-1 text-subtle-foreground">
                Section 10 — indemnification not subject to any limitation of
                liability
              </p>
            </div>
          </BrowserFrame>
        </FadeIn>
      </div>
    </SectionShell>
  );
}

/* ------------------------------------------------------------------ *
 * Negotiation agent
 * ------------------------------------------------------------------ */
export function LandingNegotiation() {
  return (
    <SectionShell
      alt
      eyebrow="Negotiation agent"
      title="Every clause checked against your playbook — nothing auto-applied"
      intro="The org configures preferred language per clause type. The agent flags any deviation (not a similarity threshold — a governing-law swap from California to Delaware scores 0.90 on difflib yet is maximally different in effect) and produces a redline. Every suggestion is pending_review."
    >
      <FadeIn>
        <BrowserFrame url="legalai.app/documents/1/negotiation" className="mx-auto max-w-2xl">
          <div className="space-y-2 font-mono text-xs">
            <p className="text-subtle-foreground">Governing law — deviation</p>
            <p className="rounded bg-danger/10 px-2 py-1 text-danger">
              − governed by the laws of the State of Delaware
            </p>
            <p className="rounded bg-success/10 px-2 py-1 text-success">
              + governed by the laws of the State of California
            </p>
            <div className="flex items-center gap-2 pt-1">
              <Badge variant="warning">pending_review</Badge>
              <span className="text-subtle-foreground">
                rationale: portfolio standard is CA jurisdiction
              </span>
            </div>
          </div>
        </BrowserFrame>
      </FadeIn>
      <MoreLink href="/features">How the drafting agent works</MoreLink>
    </SectionShell>
  );
}

/* ------------------------------------------------------------------ *
 * Evaluation framework
 * ------------------------------------------------------------------ */
export function LandingEvaluation() {
  return (
    <SectionShell
      eyebrow="Evaluation framework"
      title="A model only becomes the default when a gate proves it earns it"
      intro="The cutover gate runs a task's graded eval bound to the external baseline vs. the self-hosted candidate. passed = candidate ≥ baseline × ratio. A task routes to the self-hosted default only on a PASS — and the result is written to the eval_runs table for regression attribution."
    >
      <div className="grid gap-4 sm:grid-cols-3">
        {[
          { icon: FlaskConical, title: "Fast lane", body: "Pure-stdlib gold-set checks, CI-gated on every push — clause type, deontic tags, faithfulness." },
          { icon: CircleCheckBig, title: "Graded lane", body: "LegalBench (CUAD / ContractNLI) + MNLI loaders, SQuAD-F1 / macro-F1 metrics, no sklearn." },
          { icon: GitBranch, title: "Cutover gate", body: "Per-task meet-or-beat-baseline. \"We chose not to ship this model\" is a CI-enforced invariant." },
        ].map((f, i) => (
          <FadeIn key={f.title} delay={i * 0.05}>
            <div className="h-full rounded-xl border border-border bg-surface p-5">
              <f.icon className="size-4 text-primary" />
              <p className="mt-3 text-sm font-semibold">{f.title}</p>
              <p className="mt-1 text-sm text-muted-foreground">{f.body}</p>
            </div>
          </FadeIn>
        ))}
      </div>
      <MoreLink href="/evaluation">See the evaluation dashboard</MoreLink>
    </SectionShell>
  );
}

/* ------------------------------------------------------------------ *
 * Research contributions
 * ------------------------------------------------------------------ */
const IDEAS = [
  ["Deontic graph attention", "A GAT over an Obligation graph for cross-document conflict detection. Architecture designed; GPU training open."],
  ["Temporal obligation simulation", "Auto-derive downstream dates from \"N days after <trigger>\" patterns. CPU prototype validated against hand-modelled scenarios."],
  ["Legal-semantic fingerprinting", "Contrastive clause embeddings with verified hard negatives — modal swap, negation, magnitude shift. 122 triplets built; fine-tune GPU-blocked."],
  ["Adaptive negotiation playbook", "Procedural memory of negotiation history. Static-preference first step shipped; the full vision needs redline history."],
  ["Deontic-structure-aware ablation", "Explain a risk prediction by perturbing one legally-meaningful span at a time. Corroborated the risk model learned superficial n-grams."],
];

export function LandingResearch() {
  return (
    <SectionShell
      alt
      eyebrow="Research contributions"
      title="Five directions with potential patent value"
      intro="Each has a validated CPU prototype or a concrete design. What stays open is GPU training and the formal prior-art / patent-counsel work — both are marked as such, not hidden."
    >
      <div className="space-y-3">
        {IDEAS.map(([title, body], i) => (
          <FadeIn key={title} delay={i * 0.04}>
            <div className="flex gap-4 rounded-xl border border-border bg-surface p-5">
              <Microscope className="size-4 shrink-0 text-primary" />
              <div>
                <p className="text-sm font-semibold">{title}</p>
                <p className="mt-1 text-sm text-muted-foreground">{body}</p>
              </div>
            </div>
          </FadeIn>
        ))}
      </div>
      <MoreLink href="/research">Read the research notes</MoreLink>
    </SectionShell>
  );
}

/* ------------------------------------------------------------------ *
 * Screenshots
 * ------------------------------------------------------------------ */
export function LandingScreenshots() {
  return (
    <SectionShell
      eyebrow="Screenshots"
      title="The workspace, the trace, the router"
      intro="Previews render from the live design system — they track the current theme and never go stale."
    >
      <div className="grid gap-6 lg:grid-cols-3">
        <FadeIn>
          <BrowserFrame url="legalai.app/documents/1">
            <div className="space-y-2 text-xs">
              <div className="flex gap-1.5">
                {["Overview", "Clauses", "Risk", "Agents"].map((t, i) => (
                  <span
                    key={t}
                    className={`rounded px-2 py-1 ${i === 0 ? "bg-primary-muted text-primary" : "text-subtle-foreground"}`}
                  >
                    {t}
                  </span>
                ))}
              </div>
              <div className="h-2 w-3/4 rounded bg-elevated" />
              <div className="h-2 w-full rounded bg-elevated" />
              <div className="h-2 w-5/6 rounded bg-elevated" />
              <Badge variant="outline" className="mt-1">privileged</Badge>
            </div>
          </BrowserFrame>
        </FadeIn>
        <FadeIn delay={0.06}>
          <BrowserFrame url="legalai.app/documents/1/agents">
            <div className="space-y-1.5 font-mono text-[11px]">
              {["extraction ✓", "planner ✓", "risk_compliance ✓", "research ✓", "summary ✓", "verifier ✓"].map((s) => (
                <div key={s} className="flex items-center gap-2 text-muted-foreground">
                  <span className="size-1.5 rounded-full bg-success" />
                  {s}
                </div>
              ))}
              <p className="pt-1 text-warning">needs_human_review: KG conflict</p>
            </div>
          </BrowserFrame>
        </FadeIn>
        <FadeIn delay={0.12}>
          <BrowserFrame url="legalai.app/models">
            <div className="space-y-2 text-xs">
              {[
                ["local-llm", "B", "success"],
                ["local-embed-neural", "B", "success"],
                ["local-nli", "A", "success"],
                ["gemini", "C", "info"],
              ].map(([name, cls, tone]) => (
                <div key={name} className="flex items-center justify-between rounded-md border border-border bg-elevated px-2.5 py-1.5">
                  <span className="font-mono">{name}</span>
                  <Badge variant={tone as "success" | "info"}>Class {cls}</Badge>
                </div>
              ))}
            </div>
          </BrowserFrame>
        </FadeIn>
      </div>
    </SectionShell>
  );
}

/* ------------------------------------------------------------------ *
 * Technology stack
 * ------------------------------------------------------------------ */
const STACK = [
  ["Backend", "FastAPI · Pydantic · SQLAlchemy · Postgres / SQLite · Redis"],
  ["AI orchestration", "LangGraph · DBOS · a declarative Model Router · import-linter"],
  ["Models", "Qwen3-8B/14B (Ollama / vLLM) · bge-m3 + bge-reranker (TEI) · DeBERTa NLI · GLiNER"],
  ["Retrieval & graph", "Hybrid RAG (RRF) · rank-bm25 · FAISS · Memgraph / KùzuDB"],
  ["NLP / CV", "regex-first pipeline · dateparser · PyMuPDF · OpenCV · Tesseract"],
  ["Frontend", "Next.js · TypeScript · Tailwind · TanStack Query · React Flow · Recharts"],
  ["Eval & training", "Inspect AI · LegalBench · MLflow · DVC · Argilla"],
  ["Observability", "OpenTelemetry · a SHA-256 egress audit trail · per-call routing logs"],
];

export function LandingTechStack() {
  return (
    <SectionShell
      alt
      eyebrow="Technology stack"
      title="Everything self-hostable, nothing that phones home by default"
    >
      <div className="grid gap-4 sm:grid-cols-2">
        {STACK.map(([cat, tech], i) => (
          <FadeIn key={cat} delay={i * 0.03}>
            <div className="rounded-xl border border-border bg-surface p-5">
              <p className="text-xs font-medium uppercase tracking-wider text-subtle-foreground">
                {cat}
              </p>
              <p className="mt-2 text-sm text-muted-foreground">{tech}</p>
            </div>
          </FadeIn>
        ))}
      </div>
    </SectionShell>
  );
}

/* ------------------------------------------------------------------ *
 * Roadmap
 * ------------------------------------------------------------------ */
const PHASES = [
  ["0–4", "V1 hardening · FastAPI re-platform · CPU NLP/CV · knowledge graph + hybrid RAG · planner-driven agents with the NLI verifier", "done"],
  ["5", "Provider-agnostic Model Router · self-hosted embeddings/rerank · Gemini demoted to a Class-C plugin", "done"],
  ["6", "Self-hosted generation target (Qwen3-8B/14B) · graded eval harness + cutover gate · GLiNER NER · NLI head", "done"],
  ["7", "Sensitivity tiering enforced end-to-end · PII redaction gate + egress audit · RBAC · air-gapped packaging · KùzuDB · DBOS · memory service · first SPA", "done"],
  ["8", "Bitemporal graph versioning · consistency + simulation baselines · negotiation agent · risk dashboard + KG explorer · five NOVELTY prototypes", "done"],
  ["9", "Multi-tenant scale · SOC 2 / GDPR workflows · streaming agent trace over WebSocket · Negotiation Studio", "next"],
];

const BLOCKED = [
  ["GPU-dependent", "Fine-tuned clause-type + deontic heads, the contrastive embedding model, and the Deontic-GAT training all need a card this project doesn't have. Prototypes and pipelines are verified via dry-run / smoke."],
  ["Infrastructure-dependent", "A legal expert to adjudicate weak labels in Argilla, and qualified patent counsel for the prior-art searches. Everything up to the human step is built."],
];

export function LandingRoadmap() {
  return (
    <SectionShell
      eyebrow="Roadmap"
      title="Eight phases shipped, each one deployable"
      intro="No phase left the system in a broken state. What isn't done is either the next phase or explicitly blocked on hardware or a human — both are called out."
    >
      <div className="space-y-2">
        {PHASES.map(([label, body, status]) => (
          <FadeIn key={label}>
            <div className="flex gap-4 rounded-xl border border-border bg-surface p-4">
              <div className="w-14 shrink-0">
                <span className="font-mono text-sm font-semibold text-primary">
                  {label}
                </span>
              </div>
              <p className="flex-1 text-sm text-muted-foreground">{body}</p>
              <Badge
                variant={status === "done" ? "success" : "outline"}
                className="shrink-0 self-start"
              >
                {status === "done" ? "shipped" : "next"}
              </Badge>
            </div>
          </FadeIn>
        ))}
      </div>
      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        {BLOCKED.map(([title, body]) => (
          <FadeIn key={title}>
            <div className="rounded-xl border border-dashed border-border bg-surface/60 p-5">
              <p className="text-sm font-semibold">{title}</p>
              <p className="mt-1 text-sm text-muted-foreground">{body}</p>
            </div>
          </FadeIn>
        ))}
      </div>
      <MoreLink href="/about">The full development journey</MoreLink>
    </SectionShell>
  );
}

/* ------------------------------------------------------------------ *
 * About + docs teasers
 * ------------------------------------------------------------------ */
export function LandingAbout() {
  return (
    <SectionShell
      alt
      eyebrow="About"
      title="A serious engineering project, documented in the open"
      intro="Built solo across eight phases, with a 60-plus-entry append-only engineering journal recording every decision and every dead end."
    >
      <div className="grid gap-4 sm:grid-cols-3">
        <Link
          href="/about"
          className="group rounded-xl border border-border bg-surface p-6 transition-colors hover:border-border-strong"
        >
          <div className="flex items-center justify-between">
            <p className="text-sm font-semibold">About the project</p>
            <ArrowUpRight className="size-4 text-subtle-foreground group-hover:text-foreground" />
          </div>
          <p className="mt-2 text-sm text-muted-foreground">
            Why it was built, the design philosophy, the architecture
            decisions, the phase progression, and what&rsquo;s next.
          </p>
        </Link>
        <Link
          href="/about/developer"
          className="group rounded-xl border border-border bg-surface p-6 transition-colors hover:border-border-strong"
        >
          <div className="flex items-center justify-between">
            <p className="text-sm font-semibold">About the developer</p>
            <ArrowUpRight className="size-4 text-subtle-foreground group-hover:text-foreground" />
          </div>
          <p className="mt-2 text-sm text-muted-foreground">
            Shourya Tiwari — the skills this project exercised and what it
            taught along the way.
          </p>
        </Link>
        <Link
          href="/docs"
          className="group rounded-xl border border-border bg-surface p-6 transition-colors hover:border-border-strong"
        >
          <div className="flex items-center justify-between">
            <p className="flex items-center gap-1.5 text-sm font-semibold">
              <BookOpen className="size-4" /> Documentation
            </p>
            <ArrowUpRight className="size-4 text-subtle-foreground group-hover:text-foreground" />
          </div>
          <p className="mt-2 text-sm text-muted-foreground">
            Concepts you&rsquo;ll meet in the product, and the repository docs
            that go deeper.
          </p>
        </Link>
      </div>
      <div className="mt-6">
        <Button variant="secondary" asChild>
          <a
            href="https://github.com/shourya-tiwari/Legal-AI"
            target="_blank"
            rel="noreferrer"
          >
            <GithubIcon /> Browse the source
          </a>
        </Button>
      </div>
    </SectionShell>
  );
}
