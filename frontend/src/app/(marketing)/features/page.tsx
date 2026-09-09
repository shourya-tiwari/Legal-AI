import {
  FileSearch,
  ScanSearch,
  CalendarClock,
  Sparkles,
  Workflow,
  Network,
  GitCompareArrows,
  ShieldCheck,
  FlaskConical,
  Cpu,
} from "lucide-react";
import { MarketingHero, Section } from "@/components/marketing/section";

export const metadata = { title: "Features" };

const GROUPS = [
  {
    icon: FileSearch,
    title: "Structured understanding",
    points: [
      "Clause & sentence segmentation into typed ClauseObjects",
      "Deontic modality tagging — obligation / permission / prohibition / discretion",
      "Defined-term extraction that doubles as party identification",
      "Cross-reference resolution (“Section 4.2”, “Exhibit A”)",
      "Money / jurisdiction entities via regex, merged with GLiNER zero-shot spans",
      "Temporal expression normalisation — absolute dates resolved, durations left honest",
      "Ambiguity & vagueness detection",
    ],
  },
  {
    icon: ScanSearch,
    title: "Risk analysis",
    points: [
      "Keyword sweep across an 8-category taxonomy",
      "Contextual AI risk pass on top of the rule floor",
      "Per-category radar chart with clause-level drill-down",
      "Cross-document conflict candidates from the knowledge graph",
    ],
  },
  {
    icon: Sparkles,
    title: "Grounded generation",
    points: [
      "Plain-English rewrite — whole document or a single clause",
      "Contextualised explanation personalised to role / location / contract type",
      "Free-form Q&A grounded in the actual contract text",
      "Every answer entailment-checked; unsupported claims surfaced",
      "Retrieved sources cited by a globally-numbered [N]; fabricated citations flagged",
    ],
  },
  {
    icon: Workflow,
    title: "Agentic pipeline",
    points: [
      "A planner decides which agents run for this document",
      "Risk & compliance, clause research (hybrid RAG), summary, verifier",
      "Analysis modes: full / quick / risk-only / extract-only",
      "Full step-by-step audit trace persisted per run",
      "Verifier gate: citation validity + KG consistency + NLI faithfulness",
    ],
  },
  {
    icon: Network,
    title: "Knowledge graph",
    points: [
      "Defined terms scoped per-document, linked across the portfolio when the context matches",
      "“What else references this term” across every ingested document",
      "Candidate cross-document obligation / prohibition conflicts",
      "Bitemporal versioning — query the graph as of any point in time",
      "Interactive node/edge explorer",
    ],
  },
  {
    icon: GitCompareArrows,
    title: "Negotiation drafting",
    points: [
      "Clauses compared against your organisation's preferred language",
      "Redline diff + rationale for every deviation — flagged on any change, not a similarity threshold",
      "Always pending review; nothing is auto-applied",
      "The Verifier folds suggestions into needs_human_review",
    ],
  },
  {
    icon: CalendarClock,
    title: "Timeline & simulation",
    points: [
      "Document structure tree + descriptive timeline of dates and obligations",
      "Discrete-event simulation over resolved absolute dates",
      "Past / upcoming / future classification against a configurable warning window",
    ],
  },
  {
    icon: ShieldCheck,
    title: "Security & governance",
    points: [
      "Four-tier sensitivity classification enforced end-to-end",
      "PII redaction gate before any external dispatch",
      "SHA-256 egress audit trail",
      "Per-key and per-user RBAC with a full audit log",
      "Air-gapped build excludes the commercial provider package",
    ],
  },
  {
    icon: Cpu,
    title: "Model router",
    points: [
      "Declarative task × sensitivity × capability routing policy",
      "Class A / B / C hosting classes, self-hosted-first",
      "Per-task Class C kill switches",
      "Escalation ladder — bigger self-hosted model, never a bigger vendor",
    ],
  },
  {
    icon: FlaskConical,
    title: "Evaluation",
    points: [
      "Graded harness over LegalBench / MNLI + a hand-curated gold set",
      "Cutover gate: a task only becomes self-hosted-by-default when it meets the baseline",
      "Self-hosted-vs-external delta report",
      "Every run persisted for regression attribution",
    ],
  },
];

export default function FeaturesPage() {
  return (
    <>
      <MarketingHero
        eyebrow="Features"
        title="Ten capability areas, every one a live endpoint"
        description="Nothing here is a mockup. Each capability degrades honestly when a dependency isn't reachable."
      />
      <Section className="max-w-6xl">
        <div className="grid gap-6 md:grid-cols-2">
          {GROUPS.map((g) => (
            <div
              key={g.title}
              className="rounded-xl border border-border bg-surface p-6"
            >
              <div className="flex items-center gap-3">
                <div className="flex size-9 items-center justify-center rounded-lg bg-primary-muted text-primary">
                  <g.icon className="size-4.5" />
                </div>
                <h3 className="text-base font-semibold">{g.title}</h3>
              </div>
              <ul className="mt-4 space-y-2">
                {g.points.map((p) => (
                  <li
                    key={p}
                    className="flex gap-2.5 text-sm text-muted-foreground"
                  >
                    <span className="mt-2 size-1 shrink-0 rounded-full bg-primary" />
                    {p}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </Section>
    </>
  );
}
