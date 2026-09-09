import Link from "next/link";
import {
  Upload,
  ArrowRight,
  ScanSearch,
  Workflow,
  Network,
  ShieldCheck,
  Sparkles,
  BookOpen,
  Microscope,
  LayoutDashboard,
} from "lucide-react";
import { PageHeader, PageBody } from "@/components/layout/page-header";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { TrySampleButton } from "@/components/shared/try-sample-button";

export const metadata = { title: "Welcome" };

const STEPS = [
  {
    icon: Upload,
    title: "Upload",
    body: "PDF, DOCX, TXT, or a scanned image. Extraction runs fully local — no cloud OCR.",
  },
  {
    icon: ShieldCheck,
    title: "Classify",
    body: "A sensitivity tier is assigned on upload. Privileged text can never reach an external model.",
  },
  {
    icon: ScanSearch,
    title: "Extract",
    body: "Every clause typed and tagged — modality, defined terms, entities, dates, ambiguity.",
  },
  {
    icon: Workflow,
    title: "Analyse",
    body: "Risk radar, timeline, a planner-driven agent pipeline, the knowledge graph, negotiation redlines.",
  },
  {
    icon: Sparkles,
    title: "Verify",
    body: "Summaries and answers are entailment-checked against the source before you see them.",
  },
];

const RESOURCES = [
  {
    icon: BookOpen,
    title: "Documentation",
    body: "Concepts you'll meet in the product, and where the repo docs live.",
    href: "/docs",
  },
  {
    icon: Workflow,
    title: "Architecture",
    body: "The full system design — Model Router, pipelines, agents, data layer.",
    href: "/architecture",
  },
  {
    icon: Microscope,
    title: "Research",
    body: "Five novelty directions, from deontic graph attention to obligation simulation.",
    href: "/research",
  },
];

export default function WelcomePage() {
  return (
    <>
      <PageHeader
        title="Welcome to LegalAI"
        description="Start with your own contract, or open a sample NDA and watch the full pipeline run against it."
        actions={
          <Button variant="ghost" asChild>
            <Link href="/dashboard">
              Skip to dashboard <ArrowRight />
            </Link>
          </Button>
        }
      />
      <PageBody className="space-y-10">
        {/* Primary paths */}
        <div className="grid gap-4 lg:grid-cols-3">
          <Card className="flex flex-col border-primary/30 bg-primary-muted/30">
            <CardContent className="flex flex-1 flex-col gap-3 pt-5">
              <div className="flex size-10 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                <Upload className="size-5" />
              </div>
              <h2 className="text-base font-semibold">Upload your first contract</h2>
              <p className="flex-1 text-sm text-muted-foreground">
                The real workflow. Drop a file and go straight into the tabbed
                workspace — clauses, risk, timeline, agents, and the graph.
              </p>
              <Button asChild className="mt-2 w-full">
                <Link href="/documents/upload">
                  <Upload /> Upload a document
                </Link>
              </Button>
            </CardContent>
          </Card>

          <Card className="flex flex-col">
            <CardContent className="flex flex-1 flex-col gap-3 pt-5">
              <div className="flex size-10 items-center justify-center rounded-lg bg-elevated text-foreground">
                <Sparkles className="size-5" />
              </div>
              <h2 className="text-base font-semibold">Try a sample NDA</h2>
              <p className="flex-1 text-sm text-muted-foreground">
                A synthetic mutual NDA with a few deliberately risk-bearing
                clauses. Uploaded through the same endpoint your files use —
                nothing is stubbed.
              </p>
              <TrySampleButton className="mt-2 w-full" />
            </CardContent>
          </Card>

          <Card className="flex flex-col">
            <CardContent className="flex flex-1 flex-col gap-3 pt-5">
              <div className="flex size-10 items-center justify-center rounded-lg bg-elevated text-foreground">
                <LayoutDashboard className="size-5" />
              </div>
              <h2 className="text-base font-semibold">Look around first</h2>
              <p className="flex-1 text-sm text-muted-foreground">
                Head to the dashboard, or explore the Model Router, evaluation
                gates, and knowledge graph before you upload anything.
              </p>
              <Button variant="secondary" asChild className="mt-2 w-full">
                <Link href="/dashboard">
                  Open the dashboard <ArrowRight />
                </Link>
              </Button>
            </CardContent>
          </Card>
        </div>

        {/* How it works */}
        <section>
          <div className="flex items-center gap-2">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-subtle-foreground">
              How LegalAI works
            </h2>
            <Badge variant="outline">5 stages</Badge>
          </div>
          <ol className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
            {STEPS.map((s, i) => (
              <li
                key={s.title}
                className="rounded-xl border border-border bg-surface p-4"
              >
                <div className="flex items-center gap-2">
                  <span className="flex size-6 items-center justify-center rounded-full bg-primary-muted text-xs font-semibold text-primary">
                    {i + 1}
                  </span>
                  <s.icon className="size-4 text-subtle-foreground" />
                </div>
                <p className="mt-2 text-sm font-semibold">{s.title}</p>
                <p className="mt-1 text-xs text-muted-foreground">{s.body}</p>
              </li>
            ))}
          </ol>
        </section>

        {/* Learn more */}
        <section>
          <h2 className="text-sm font-semibold uppercase tracking-wider text-subtle-foreground">
            Learn the platform
          </h2>
          <div className="mt-4 grid gap-4 sm:grid-cols-3">
            {RESOURCES.map((r) => (
              <Link
                key={r.title}
                href={r.href}
                className="group rounded-xl border border-border bg-surface p-5 transition-colors hover:border-border-strong"
              >
                <div className="flex items-center justify-between">
                  <div className="flex size-9 items-center justify-center rounded-lg bg-elevated text-foreground">
                    <r.icon className="size-4" />
                  </div>
                  <ArrowRight className="size-4 text-subtle-foreground transition-transform group-hover:translate-x-0.5" />
                </div>
                <p className="mt-3 text-sm font-semibold">{r.title}</p>
                <p className="mt-1 text-sm text-muted-foreground">{r.body}</p>
              </Link>
            ))}
          </div>
        </section>

        <div className="flex items-center gap-3 rounded-xl border border-border bg-surface/60 p-4 text-sm text-muted-foreground">
          <Network className="size-4 shrink-0 text-subtle-foreground" />
          <span>
            No account is needed in local development, and the platform runs with
            zero model credentials — embeddings fall back to a local provider and
            generation raises a clear error until you configure one.
          </span>
        </div>
      </PageBody>
    </>
  );
}
