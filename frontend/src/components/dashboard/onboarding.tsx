"use client";

import Link from "next/link";
import {
  Upload,
  ArrowRight,
  BookOpen,
  Layers,
  Workflow,
  Compass,
  ScanSearch,
  Network,
  GitCompareArrows,
  Sparkles,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { TrySampleButton } from "@/components/shared/try-sample-button";

const QUICK_LINKS = [
  {
    icon: Compass,
    title: "Guided start",
    body: "The three ways in, plus a walkthrough of the pipeline.",
    href: "/welcome",
  },
  {
    icon: BookOpen,
    title: "Documentation",
    body: "Concepts you'll meet in the product and where the repo docs live.",
    href: "/docs",
  },
  {
    icon: Layers,
    title: "Explore features",
    body: "Every capability, mapped — structure, risk, agents, graph, negotiation.",
    href: "/features",
  },
  {
    icon: Workflow,
    title: "Architecture overview",
    body: "Model Router, the rule-first pipelines, the agent graph, the data layer.",
    href: "/architecture",
  },
];

const CAPABILITIES = [
  {
    icon: ScanSearch,
    title: "Risk radar",
    body: "Eight categories, keyword + contextual detection, clause-level drill-down.",
  },
  {
    icon: Sparkles,
    title: "Grounded answers",
    body: "Every answer entailment-checked against the contract; unsupported claims surfaced.",
  },
  {
    icon: Network,
    title: "Portfolio knowledge graph",
    body: "Defined terms linked across documents, candidate cross-document conflicts.",
  },
  {
    icon: GitCompareArrows,
    title: "Negotiation redlines",
    body: "Each clause compared to your playbook, with a diff and a rationale. Never auto-applied.",
  },
];

export function DashboardOnboarding() {
  return (
    <div className="space-y-8">
      {/* Hero */}
      <Card className="overflow-hidden border-primary/25">
        <CardContent className="relative pt-6">
          <div className="absolute inset-0 -z-10 bg-dots opacity-40" />
          <Badge variant="primary" className="gap-1.5">
            <span className="size-1.5 rounded-full bg-primary-foreground/80" />
            Your workspace is ready
          </Badge>
          <h2 className="mt-3 max-w-xl text-2xl font-semibold tracking-tight">
            Upload a contract to see the whole pipeline run against it
          </h2>
          <p className="mt-2 max-w-xl text-sm text-muted-foreground">
            Clause extraction, the risk radar, the timeline, a planner-driven
            agent pipeline with faithfulness verification, and the knowledge
            graph — all against the real document, nothing stubbed.
          </p>
          <div className="mt-5 flex flex-col gap-3 sm:flex-row">
            <Button size="lg" asChild>
              <Link href="/documents/upload">
                <Upload /> Upload your first contract
              </Link>
            </Button>
            <TrySampleButton size="lg" />
          </div>
        </CardContent>
      </Card>

      {/* Quick links */}
      <div>
        <h3 className="text-sm font-semibold uppercase tracking-wider text-subtle-foreground">
          Learn the product
        </h3>
        <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {QUICK_LINKS.map((q) => (
            <Link
              key={q.title}
              href={q.href}
              className="group rounded-xl border border-border bg-surface p-5 transition-colors hover:border-border-strong"
            >
              <div className="flex items-center justify-between">
                <div className="flex size-9 items-center justify-center rounded-lg bg-elevated text-foreground">
                  <q.icon className="size-4" />
                </div>
                <ArrowRight className="size-4 text-subtle-foreground transition-transform group-hover:translate-x-0.5" />
              </div>
              <p className="mt-3 text-sm font-semibold">{q.title}</p>
              <p className="mt-1 text-sm text-muted-foreground">{q.body}</p>
            </Link>
          ))}
        </div>
      </div>

      {/* Capabilities preview */}
      <div>
        <h3 className="text-sm font-semibold uppercase tracking-wider text-subtle-foreground">
          What you&rsquo;ll get on every document
        </h3>
        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          {CAPABILITIES.map((c) => (
            <div
              key={c.title}
              className="flex gap-3 rounded-xl border border-border bg-surface p-4"
            >
              <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-primary-muted text-primary">
                <c.icon className="size-4" />
              </div>
              <div>
                <p className="text-sm font-semibold">{c.title}</p>
                <p className="mt-0.5 text-sm text-muted-foreground">{c.body}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
