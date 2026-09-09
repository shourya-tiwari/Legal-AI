import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { FadeIn } from "./fade-in";

const NUMBERS = [
  ["8", "delivery phases, each deployable"],
  ["40+", "API endpoints, all typed"],
  ["400+", "backend tests, green"],
  ["4", "sensitivity tiers, enforced end-to-end"],
  ["0", "model credentials required to run"],
];

const REASONS = [
  {
    title: "It runs disconnected",
    body: "The air-gapped build excludes the commercial-provider package entirely. Structure, retrieval, the knowledge graph, agents, and sensitivity classification are all CPU-fine; generation runs on a 16 GB card or a small CPU model.",
  },
  {
    title: "The verifier can fail",
    body: "Every agent summary and every grounded answer is entailment-checked against its sources. Contradicted or unsupported claims are surfaced — the product tells you when it isn't sure.",
  },
  {
    title: "Model choices are gated",
    body: "A task only becomes self-hosted-by-default when a cutover gate proves the local model meets or beats the external baseline. \"We chose not to ship this model\" is a CI-enforced invariant.",
  },
  {
    title: "Nothing is auto-applied",
    body: "Negotiation redlines, sensitivity overrides, and flagged analyses all route through a human. The review queue is a real queue, not a documented intention.",
  },
];

const FAQ = [
  [
    "Does my contract text leave my infrastructure?",
    "Only if you let it, and only for public/internal-tier documents. Confidential and privileged documents are structurally unable to reach an external provider — the router fails closed. A PII redaction gate masks identifiers before any external call, and every such call is logged with a SHA-256 of the exact text sent (never the payload).",
  ],
  [
    "What model does it use?",
    "Whatever you configure. The default target is a self-hosted Qwen3-8B/14B, with embeddings and reranking on TEI. Gemini is an optional Class-C plugin for public/internal documents where a cutover gate shows it wins. With no credentials at all, embeddings fall to a local hashing provider and generation raises a clear error.",
  ],
  [
    "Is this production-ready?",
    "The backend is feature-complete for a single-tenant / small-team deployment and has on-prem, air-gapped, and collapsed-data-layer packaging. Multi-tenant scale, SOC 2, and GDPR workflows are the Phase 9 roadmap.",
  ],
  [
    "Can I see how it works?",
    "Yes — the whole pipeline is inspectable. The agent trace shows every step, the routing decision is logged per call, the knowledge graph is an interactive canvas, and the evaluation dashboard shows exactly which tasks cut over to self-hosted and why.",
  ],
  [
    "What's the research angle?",
    "Five directions with potential patent value — deontic graph attention for conflict detection, temporal obligation simulation, legal-semantic fingerprinting, adaptive negotiation playbooks, and deontic-structure-aware ablation. CPU prototypes are validated; the GPU training and formal prior-art searches are the open work.",
  ],
];

export function HomeNumbers() {
  return (
    <section className="border-y border-border bg-surface/40">
      <div className="mx-auto grid w-full max-w-6xl grid-cols-2 gap-6 px-4 py-12 sm:px-6 md:grid-cols-5">
        {NUMBERS.map(([n, label], i) => (
          <FadeIn key={label} delay={i * 0.05} className="text-center">
            <p className="text-3xl font-semibold tracking-tight">{n}</p>
            <p className="mt-1 text-xs text-muted-foreground">{label}</p>
          </FadeIn>
        ))}
      </div>
    </section>
  );
}

export function HomeReasons() {
  return (
    <section className="mx-auto w-full max-w-6xl px-4 py-20 sm:px-6">
      <FadeIn>
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">
            Why this platform
          </h2>
          <p className="mt-3 text-muted-foreground">
            Four decisions that shaped it.
          </p>
        </div>
      </FadeIn>
      <div className="mt-12 grid gap-4 md:grid-cols-2">
        {REASONS.map((r, i) => (
          <FadeIn key={r.title} delay={i * 0.05}>
            <div className="h-full rounded-xl border border-border bg-surface p-6">
              <h3 className="text-sm font-semibold">{r.title}</h3>
              <p className="mt-1.5 text-sm text-muted-foreground">{r.body}</p>
            </div>
          </FadeIn>
        ))}
      </div>
    </section>
  );
}


export function HomeFaq() {
  return (
    <section className="mx-auto w-full max-w-3xl px-4 py-20 sm:px-6">
      <FadeIn>
        <h2 className="text-center text-2xl font-semibold tracking-tight sm:text-3xl">
          Frequently asked
        </h2>
      </FadeIn>
      <div className="mt-10">
        <Accordion type="single" collapsible className="w-full">
          {FAQ.map(([q, a], i) => (
            <AccordionItem key={i} value={`faq-${i}`}>
              <AccordionTrigger>{q}</AccordionTrigger>
              <AccordionContent>{a}</AccordionContent>
            </AccordionItem>
          ))}
        </Accordion>
      </div>
    </section>
  );
}
