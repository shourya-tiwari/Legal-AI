import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { GithubIcon } from "@/components/shared/brand-icons";
import { Button } from "@/components/ui/button";

export const metadata = {
  title: "About the project",
  description:
    "An engineering case study: how LegalAI evolved from a single-model Gemini demo into a self-hosted, provider-agnostic legal reasoning platform.",
};

const PHASES = [
  ["Phase 0–1", "V1 hardening, then a FastAPI re-platform: Postgres/Redis, org-scoped auth, document persistence, a provider-agnostic Model Router seam."],
  ["Phase 2", "CPU NLP + CV pipelines turn flat text into a structured ClauseObject graph — segmentation, defined terms, deontic tagging, temporal normalisation, ambiguity detection."],
  ["Phase 3", "Knowledge Graph (Memgraph) + hybrid RAG (dense + sparse + graph, RRF fusion) replace a hardcoded knowledge base."],
  ["Phase 4", "A planner-driven LangGraph agent pipeline with a real NLI faithfulness verifier gating every summary."],
  ["Phase 5", "The Model Router becomes genuinely provider-agnostic: embeddings and reranking self-hosted, Gemini demoted to an optional Class C plugin, an import-linter contract enforcing the boundary."],
  ["Phase 6", "Self-hosted generation target (Qwen3-8B/14B), a graded eval harness with a cutover gate, GLiNER NER, the NLI head."],
  ["Phase 7", "Document sensitivity tiering enforced end-to-end, a PII redaction gate + egress audit trail, per-user identity + RBAC, on-prem/air-gapped packaging, a collapsed data layer (KùzuDB), durable execution (DBOS), a three-tier memory service, and the first Next.js SPA."],
  ["Phase 8", "Bitemporal graph versioning, cross-document consistency + simulation baselines, a negotiation drafting agent, the risk dashboard, and five research prototypes from NOVELTY.md."],
];

export default function AboutPage() {
  return (
    <div className="mx-auto w-full max-w-3xl px-4 py-16 sm:px-6">
      <p className="text-sm font-medium text-primary">Engineering case study</p>
      <h1 className="mt-2 text-3xl font-semibold tracking-tight sm:text-4xl">
        From a Gemini demo to a self-hosted legal reasoning platform
      </h1>
      <p className="mt-5 text-lg text-muted-foreground">
        LegalAI started as a thin wrapper around one external model. It is now a
        provider-agnostic system where the domain quality comes from retrieval,
        a knowledge graph, fine-tuned heads, and a verifier — not from model
        scale — and where the deployment can run completely disconnected.
      </p>

      <div className="mt-12 space-y-6">
        {PHASES.map(([label, body]) => (
          <div key={label} className="flex gap-4">
            <div className="w-20 shrink-0 pt-0.5 text-sm font-semibold text-primary">
              {label}
            </div>
            <p className="text-sm text-muted-foreground">{body}</p>
          </div>
        ))}
      </div>

      <div className="mt-12 rounded-xl border border-border bg-surface p-6">
        <h2 className="text-sm font-semibold">The through-line</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          Every phase moved inference toward the organisation&rsquo;s own
          hardware and away from any external dependency. The bounded GPU
          reality — one 16&nbsp;GB card — forced the architecture to be honest:
          an 8–14&nbsp;B model plus strong retrieval and fine-tuned classifiers,
          with an external API kept only where a cutover gate proves it wins.
        </p>
      </div>

      <div className="mt-10 flex flex-wrap gap-3">
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
    </div>
  );
}
