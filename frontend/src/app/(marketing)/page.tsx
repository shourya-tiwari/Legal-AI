import Link from "next/link";
import {
  ArrowRight,
  ShieldCheck,
  Network,
  Workflow,
  ScanSearch,
  GitCompareArrows,
  Sparkles,
  FileSearch,
  CircleCheckBig,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

export const metadata = {
  title: "Self-hosted legal contract intelligence",
};

const FEATURES = [
  {
    icon: FileSearch,
    title: "Structured clause extraction",
    body: "Every clause typed and tagged — deontic modality, defined terms, cross-references, entities, temporal expressions, ambiguity flags. Rule-based first, neural where it earns it.",
  },
  {
    icon: ScanSearch,
    title: "Risk radar",
    body: "Keyword + contextual detection across eight categories, aggregated into a spider chart with clause-level drill-down. Uncapped liability, unilateral termination, one-sided arbitration.",
  },
  {
    icon: Sparkles,
    title: "Grounded answers",
    body: "Ask anything about a contract and get an answer checked against the actual text by an NLI entailment head — unsupported claims are surfaced, not hidden.",
  },
  {
    icon: Workflow,
    title: "Planner-driven agents",
    body: "A pipeline that decides which agents to run, researches flagged clauses, checks the knowledge graph for conflicts, and verifies its own summary before you see it.",
  },
  {
    icon: Network,
    title: "Portfolio knowledge graph",
    body: "Defined terms linked across documents, candidate cross-document conflicts, bitemporal version history — explore it as an interactive graph.",
  },
  {
    icon: GitCompareArrows,
    title: "Negotiation drafting",
    body: "Clauses compared against your organisation's preferred language, with a redline diff and rationale. Every suggestion is pending review — nothing is auto-applied.",
  },
];

const PIPELINE = [
  { label: "Upload", body: "PDF, DOCX, TXT, or a scanned image." },
  { label: "Classify", body: "Sensitivity tier assigned — privileged text never leaves the perimeter." },
  { label: "Extract", body: "Structured clause graph, not just flat text." },
  { label: "Analyse", body: "Risk, timeline, agents, knowledge graph, negotiation." },
  { label: "Verify", body: "Faithfulness-checked before it reaches you." },
];

export default function HomePage() {
  return (
    <>
      {/* Hero */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 -z-10 bg-grid opacity-60" />
        <div
          className="absolute inset-x-0 top-0 -z-10 h-[500px] opacity-70"
          style={{
            background:
              "radial-gradient(ellipse 60% 50% at 50% 0%, color-mix(in oklch, var(--color-primary) 22%, transparent), transparent)",
          }}
        />
        <div className="mx-auto flex w-full max-w-5xl flex-col items-center px-4 pb-20 pt-20 text-center sm:px-6 sm:pt-28">
          <Badge variant="outline" className="mb-6 gap-1.5 py-1">
            <span className="size-1.5 rounded-full bg-success" />
            Self-hosted · provider-agnostic · air-gap ready
          </Badge>
          <h1 className="max-w-3xl text-4xl font-semibold tracking-tight text-balance sm:text-6xl">
            Contract intelligence that{" "}
            <span className="text-gradient">stays inside your walls</span>
          </h1>
          <p className="mt-6 max-w-2xl text-base text-muted-foreground text-pretty sm:text-lg">
            Clause extraction, risk analysis, plain-English rewrites, a
            planner-driven agent pipeline with faithfulness verification, a
            portfolio knowledge graph, and negotiation drafting — with every
            model call routed by sensitivity tier.
          </p>
          <div className="mt-9 flex flex-col gap-3 sm:flex-row">
            <Button size="lg" asChild>
              <Link href="/dashboard">
                Get Started <ArrowRight />
              </Link>
            </Button>
            <Button size="lg" variant="secondary" asChild>
              <Link href="/features">Explore Features</Link>
            </Button>
          </div>
          <p className="mt-4 text-xs text-subtle-foreground">
            No account needed in local development. Runs with zero model
            credentials.
          </p>
        </div>
      </section>

      {/* Pipeline strip */}
      <section className="border-y border-border bg-surface/40">
        <div className="mx-auto w-full max-w-6xl px-4 py-10 sm:px-6">
          <ol className="grid gap-6 sm:grid-cols-3 lg:grid-cols-5">
            {PIPELINE.map((step, i) => (
              <li key={step.label} className="flex flex-col gap-1.5">
                <div className="flex items-center gap-2">
                  <span className="flex size-6 items-center justify-center rounded-full bg-primary-muted text-xs font-semibold text-primary">
                    {i + 1}
                  </span>
                  <span className="text-sm font-semibold">{step.label}</span>
                </div>
                <p className="text-xs text-muted-foreground">{step.body}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* Features */}
      <section className="mx-auto w-full max-w-6xl px-4 py-20 sm:px-6">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">
            Everything runs against the real document
          </h2>
          <p className="mt-3 text-muted-foreground">
            Not a demo. Every capability below is a live endpoint with an
            honest &ldquo;knowledge graph offline&rdquo; state when a service
            isn&rsquo;t reachable.
          </p>
        </div>
        <div className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((f) => (
            <div
              key={f.title}
              className="group rounded-xl border border-border bg-surface p-6 transition-colors hover:border-border-strong"
            >
              <div className="flex size-10 items-center justify-center rounded-lg bg-primary-muted text-primary">
                <f.icon className="size-5" />
              </div>
              <h3 className="mt-4 text-sm font-semibold">{f.title}</h3>
              <p className="mt-1.5 text-sm text-muted-foreground">{f.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Security */}
      <section className="border-t border-border bg-surface/40">
        <div className="mx-auto grid w-full max-w-6xl gap-10 px-4 py-20 sm:px-6 lg:grid-cols-2 lg:items-center">
          <div>
            <Badge variant="primary" className="mb-4">
              <ShieldCheck />
              Sensitivity-tiered routing
            </Badge>
            <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">
              Privileged text never leaves the perimeter
            </h2>
            <p className="mt-4 text-muted-foreground">
              Every document is classified <code>public</code>,{" "}
              <code>internal</code>, <code>confidential</code>, or{" "}
              <code>privileged</code> on upload. The Model Router fails closed:
              confidential and privileged documents are structurally unable to
              reach an external provider, and a PII redaction gate masks
              identifiers before any Class C call.
            </p>
            <ul className="mt-6 space-y-2.5">
              {[
                "Regex + NER redaction gate before every external dispatch",
                "SHA-256 egress audit trail — what left, never the payload",
                "Air-gapped build excludes the commercial provider package entirely",
                "Per-key and per-user RBAC with a full audit log",
              ].map((item) => (
                <li key={item} className="flex items-start gap-2.5 text-sm">
                  <CircleCheckBig className="mt-0.5 size-4 shrink-0 text-success" />
                  <span className="text-muted-foreground">{item}</span>
                </li>
              ))}
            </ul>
          </div>
          <div className="rounded-xl border border-border bg-background p-6 font-mono text-xs shadow-sm">
            <p className="text-subtle-foreground"># routing decision</p>
            <p className="mt-2">
              <span className="text-info">task</span>{" "}
              <span className="text-foreground">clause_rewrite</span>
            </p>
            <p>
              <span className="text-info">sensitivity</span>{" "}
              <span className="text-warning">privileged</span>
            </p>
            <p>
              <span className="text-info">candidates</span>{" "}
              <span className="text-muted-foreground">
                [local-llm, local-llm-large]
              </span>
            </p>
            <p className="text-danger">
              class_c_candidates dropped: gemini (tier not permitted)
            </p>
            <p className="mt-2 text-success">
              → resolved: local-llm-large (self-hosted)
            </p>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="mx-auto w-full max-w-4xl px-4 py-20 sm:px-6">
        <div className="relative overflow-hidden rounded-2xl border border-border bg-surface px-8 py-14 text-center">
          <div className="absolute inset-0 -z-10 bg-dots opacity-40" />
          <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">
            Open the workspace
          </h2>
          <p className="mx-auto mt-3 max-w-md text-muted-foreground">
            Upload a contract and see clause extraction, the risk radar, the
            agent trace, and the knowledge graph run against it.
          </p>
          <Button size="lg" asChild className="mt-7">
            <Link href="/dashboard">
              Get Started <ArrowRight />
            </Link>
          </Button>
        </div>
      </section>
    </>
  );
}
