import { MarketingHero, Section, SectionTitle } from "@/components/marketing/section";

export const metadata = { title: "Architecture" };

const LAYERS = [
  {
    name: "Client",
    tech: "Next.js · TypeScript · Tailwind · TanStack Query",
    body: "A client-rendered SPA against a separate FastAPI origin. Auth optional; token stored client-side when on.",
  },
  {
    name: "API",
    tech: "FastAPI · Pydantic · one guard per route",
    body: "Thin route → service modules. Every route behind api_guard (auth + rate limit + audit). Additive /api/v2/* document-first surface.",
  },
  {
    name: "Model Router",
    tech: "declarative policy · import-linter contract",
    body: "Every AI call names a task, never a model. Class A/B/C providers; self-hosted-first chains; Class C appended only when the sensitivity tier permits.",
  },
  {
    name: "Pipelines",
    tech: "rule-based first · neural where it earns it",
    body: "NLP (segmentation, deontic, entities, temporal, ambiguity) and CV (blur/skew/redaction triage) turn flat text into a structured ClauseObject graph.",
  },
  {
    name: "Agents",
    tech: "LangGraph · planner-driven · DBOS optional",
    body: "extraction → planner → dispatch-by-plan → verifier. Each node wraps a service. The verifier is the mandatory release gate.",
  },
  {
    name: "Knowledge & retrieval",
    tech: "Memgraph / KùzuDB · hybrid RAG (RRF)",
    body: "Dense + sparse + graph retrieval fused by reciprocal rank fusion. Bitemporal graph versioning.",
  },
  {
    name: "Data",
    tech: "Postgres / SQLite · Redis · content-addressed blobs",
    body: "Documents, audit log, agent traces, case analyses, model calls, eval runs. Interim column-migration shim before Alembic.",
  },
];

const PIPELINE = [
  "Upload",
  "Extract (PyMuPDF / python-docx / OCR)",
  "Classify sensitivity",
  "Segment → ClauseObjects",
  "Planner",
  "Risk · Research · Summary",
  "Verifier (citation · KG · NLI)",
  "Persist trace + case analysis",
];

export default function ArchitecturePage() {
  return (
    <>
      <MarketingHero
        eyebrow="Architecture"
        title="Self-hosting is the spine, not a top-up"
        description="Every phase moved inference toward the organisation's own hardware. The domain quality comes from retrieval, the knowledge graph, fine-tuned heads, and the verifier — not from model scale."
      />

      <Section>
        <SectionTitle subtitle="A request from upload to a verified result.">
          The analysis pipeline
        </SectionTitle>
        <ol className="mx-auto mt-10 flex max-w-3xl flex-col gap-0">
          {PIPELINE.map((step, i) => (
            <li key={step} className="flex gap-4">
              <div className="flex flex-col items-center">
                <span className="flex size-8 shrink-0 items-center justify-center rounded-full border border-border bg-surface text-xs font-semibold">
                  {i + 1}
                </span>
                {i < PIPELINE.length - 1 && (
                  <span className="my-1 h-8 w-px bg-border" />
                )}
              </div>
              <p className="pt-1.5 text-sm">{step}</p>
            </li>
          ))}
        </ol>
      </Section>

      <Section className="border-t border-border">
        <SectionTitle subtitle="Seven layers, each replaceable without touching the others.">
          The layers
        </SectionTitle>
        <div className="mt-10 space-y-3">
          {LAYERS.map((l) => (
            <div
              key={l.name}
              className="grid gap-2 rounded-xl border border-border bg-surface p-5 sm:grid-cols-[160px_1fr]"
            >
              <div>
                <p className="text-sm font-semibold">{l.name}</p>
                <p className="text-xs text-subtle-foreground">{l.tech}</p>
              </div>
              <p className="text-sm text-muted-foreground">{l.body}</p>
            </div>
          ))}
        </div>
      </Section>
    </>
  );
}
