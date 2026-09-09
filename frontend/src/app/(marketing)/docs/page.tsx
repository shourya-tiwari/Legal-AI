import Link from "next/link";
import { ArrowUpRight, BookOpen } from "lucide-react";
import { MarketingHero, Section } from "@/components/marketing/section";

export const metadata = { title: "Documentation" };

const CONCEPTS = [
  {
    title: "Sensitivity tiering",
    body: "How a document gets a tier and what the Model Router does with it.",
    href: "/architecture",
  },
  {
    title: "The Model Router",
    body: "Task-named calls, hosting classes, the declarative routing policy, and Class-C gating.",
    href: "/models",
  },
  {
    title: "The agent pipeline",
    body: "Planner-driven dispatch, the verifier gate, and the persisted trace.",
    href: "/features",
  },
  {
    title: "Faithfulness verification",
    body: "The NLI entailment head, the lexical fallback, and where the check runs.",
    href: "/features",
  },
  {
    title: "The knowledge graph",
    body: "Per-document defined terms, portfolio linking, conflicts, bitemporal versioning.",
    href: "/knowledge-graph",
  },
  {
    title: "Evaluation & cutover gates",
    body: "The graded harness, the meet-or-beat-baseline rule, and per-task cutover.",
    href: "/evaluation",
  },
];

const REPO_DOCS = [
  ["README.md", "Quick start, API reference, environment variables"],
  ["docs/v2/ARCHITECTURE.md", "The full target architecture"],
  ["docs/v2/ROADMAP.md", "Phase-by-phase delivery plan and current status"],
  ["docs/v2/AI_STACK.md", "The provider-agnostic model stack"],
  ["docs/v2/NLP.md", "The rule-first NLP pipeline"],
  ["docs/v2/KNOWLEDGE_GRAPH.md", "Graph schema and queries"],
  ["docs/v2/AGENTS.md", "Agent responsibilities and the memory service"],
  ["docs/v2/NOVELTY.md", "The five research directions"],
  ["docs/v2/FRONTEND_PLAN.md", "This frontend's implementation plan"],
  ["CHANGELOG.md", "Release notes"],
];

export default function DocsPage() {
  return (
    <>
      <MarketingHero
        eyebrow="Documentation"
        title="Concepts, and where they live"
        description="The platform documentation is maintained in the repository. This hub links the concepts you'll meet in the product."
      />
      <Section>
        <h2 className="text-lg font-semibold">Concepts</h2>
        <div className="mt-5 grid gap-4 sm:grid-cols-2">
          {CONCEPTS.map((c) => (
            <Link
              key={c.title}
              href={c.href}
              className="group rounded-xl border border-border bg-surface p-5 transition-colors hover:border-border-strong"
            >
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold">{c.title}</h3>
                <ArrowUpRight className="size-4 text-subtle-foreground transition-colors group-hover:text-foreground" />
              </div>
              <p className="mt-1.5 text-sm text-muted-foreground">{c.body}</p>
            </Link>
          ))}
        </div>

        <h2 className="mt-14 text-lg font-semibold">In the repository</h2>
        <div className="mt-5 overflow-hidden rounded-xl border border-border">
          <ul className="divide-y divide-border">
            {REPO_DOCS.map(([path, desc]) => (
              <li
                key={path}
                className="flex items-center gap-3 px-4 py-3 text-sm"
              >
                <BookOpen className="size-4 shrink-0 text-subtle-foreground" />
                <code className="shrink-0 text-xs text-primary">{path}</code>
                <span className="truncate text-muted-foreground">{desc}</span>
              </li>
            ))}
          </ul>
        </div>
        <p className="mt-4 text-sm text-muted-foreground">
          Full source:{" "}
          <a
            href="https://github.com/shourya-tiwari/Legal-AI"
            target="_blank"
            rel="noreferrer"
            className="font-medium text-primary hover:underline"
          >
            github.com/shourya-tiwari/Legal-AI
          </a>
        </p>
      </Section>
    </>
  );
}
