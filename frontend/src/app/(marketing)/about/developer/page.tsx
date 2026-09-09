import Link from "next/link";
import { Mail, ArrowLeft, Download } from "lucide-react";
import { GithubIcon, LinkedinIcon } from "@/components/shared/brand-icons";
import { MarketingHero, Section } from "@/components/marketing/section";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

export const metadata = { title: "About the developer" };

const SKILLS = {
  "Languages": ["TypeScript", "Python", "SQL", "Cypher"],
  "Frontend": ["Next.js", "React", "Tailwind", "TanStack Query", "React Flow"],
  "Backend": ["FastAPI", "SQLAlchemy", "Pydantic", "LangGraph", "DBOS"],
  "ML / AI": ["Model routing", "RAG", "NLI verification", "GLiNER", "LoRA fine-tuning", "MLflow / DVC"],
  "Data": ["Postgres", "Redis", "Memgraph", "KùzuDB", "FAISS"],
  "Infra": ["Docker", "Kustomize / Helm", "Zarf", "GitHub Actions", "OpenTelemetry"],
};

const STATS = [
  ["8", "delivery phases"],
  ["62", "engineering-journal entries"],
  ["400+", "backend tests"],
  ["40+", "API endpoints"],
  ["5", "research prototypes"],
];

export default function DeveloperPage() {
  return (
    <>
      <MarketingHero
        eyebrow="About the developer"
        title="Shourya Tiwari"
        description="Full-stack engineer with a focus on applied AI systems — retrieval, agents, evaluation, and the infrastructure to keep them honest."
      >
        <div className="flex flex-wrap justify-center gap-3">
          <Button asChild>
            <a
              href="https://github.com/shourya-tiwari"
              target="_blank"
              rel="noreferrer"
            >
              <GithubIcon /> GitHub
            </a>
          </Button>
          <Button variant="secondary" asChild>
            <a href="https://www.linkedin.com/" target="_blank" rel="noreferrer">
              <LinkedinIcon /> LinkedIn
            </a>
          </Button>
          <Button variant="secondary" asChild>
            <a href="mailto:tshourya1507@gmail.com">
              <Mail /> Email
            </a>
          </Button>
          <Button variant="outline" disabled>
            <Download /> Résumé (coming soon)
          </Button>
        </div>
      </MarketingHero>

      <Section className="max-w-4xl">
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-5">
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

        <div className="mt-12 space-y-6">
          <h2 className="text-lg font-semibold">Skills</h2>
          {Object.entries(SKILLS).map(([group, items]) => (
            <div key={group} className="flex flex-col gap-2 sm:flex-row">
              <p className="w-28 shrink-0 text-sm font-medium text-muted-foreground">
                {group}
              </p>
              <div className="flex flex-wrap gap-1.5">
                {items.map((s) => (
                  <Badge key={s} variant="outline">
                    {s}
                  </Badge>
                ))}
              </div>
            </div>
          ))}
        </div>

        <div className="mt-12 rounded-xl border border-border bg-surface p-6">
          <h2 className="text-sm font-semibold">What this project taught me</h2>
          <ul className="mt-3 space-y-2 text-sm text-muted-foreground">
            <li>
              • Provider-agnosticism is an architecture decision, not a config
              flag — it has to be enforced (an import-linter contract) or it
              rots.
            </li>
            <li>
              • A verifier that can fail is worth more than a model that&rsquo;s
              usually right. Faithfulness checking changed what the product
              could honestly claim.
            </li>
            <li>
              • Eval gates make &ldquo;we chose not to ship this model&rdquo; a
              CI-enforced invariant instead of a footnote.
            </li>
            <li>
              • Most &ldquo;blocked&rdquo; items weren&rsquo;t — re-checking the
              actual environment beat assuming.
            </li>
          </ul>
        </div>

        <div className="mt-10">
          <Button variant="ghost" asChild>
            <Link href="/about">
              <ArrowLeft /> The project story
            </Link>
          </Button>
        </div>
      </Section>
    </>
  );
}
