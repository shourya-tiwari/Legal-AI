"use client";

import * as React from "react";
import Link from "next/link";
import {
  Workflow,
  ShieldAlert,
  RefreshCw,
  ChevronRight,
  CircleDot,
} from "lucide-react";
import { useWorkspace } from "@/components/workspace/workspace-context";
import { useAnalysis } from "@/components/workspace/use-analysis";
import { RunAnalysisCta } from "@/components/workspace/run-analysis-cta";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { FaithfulnessBadge } from "@/components/shared/faithfulness-badge";
import type { AnalysisMode } from "@/lib/api";
import { titleCase } from "@/lib/format";

export default function AgentsPage() {
  const { id } = useWorkspace();
  const [mode, setMode] = React.useState<AnalysisMode>("full");
  const [aiPlanner, setAiPlanner] = React.useState(false);
  const analysis = useAnalysis(id, mode, aiPlanner);
  const d = analysis.data;

  return (
    <div className="space-y-6">
      <Card>
        <CardContent className="flex flex-col gap-4 pt-5 sm:flex-row sm:items-end">
          <div className="space-y-1.5">
            <Label htmlFor="mode">Analysis mode</Label>
            <Select
              value={mode}
              onValueChange={(v) => setMode(v as AnalysisMode)}
            >
              <SelectTrigger id="mode" className="w-44">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="full">Full</SelectItem>
                <SelectItem value="quick">Quick (skip research)</SelectItem>
                <SelectItem value="risk_only">Risk only</SelectItem>
                <SelectItem value="extract_only">Extract only</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="flex items-center gap-2 pb-2">
            <Switch
              id="planner"
              checked={aiPlanner}
              onCheckedChange={setAiPlanner}
            />
            <Label htmlFor="planner" className="text-sm">
              AI planner
            </Label>
          </div>
          <div className="flex flex-1 justify-end">
            <Button
              onClick={() => analysis.run()}
              loading={analysis.isPending}
              variant={analysis.hasRun ? "secondary" : "primary"}
            >
              <RefreshCw />
              {analysis.hasRun ? "Re-run" : "Run analysis"}
            </Button>
          </div>
        </CardContent>
      </Card>

      {!analysis.hasRun ? (
        <RunAnalysisCta
          title="Run the agent pipeline"
          description="The planner picks which agents run, then research, summary, and the verifier gate. Every step is captured."
          isPending={analysis.isPending}
          isError={analysis.isError}
          error={analysis.error}
          onRun={() => analysis.run()}
        />
      ) : d ? (
        <>
          {/* Plan */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Workflow className="size-4" /> Planner
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex flex-wrap items-center gap-2">
                {(d.plan ?? []).map((node, i) => (
                  <React.Fragment key={node}>
                    {i > 0 && (
                      <ChevronRight className="size-3.5 text-subtle-foreground" />
                    )}
                    <span
                      className={`rounded-lg border px-2.5 py-1 text-xs font-medium ${
                        node === "verifier"
                          ? "border-primary/40 bg-primary-muted text-primary"
                          : "border-border bg-surface"
                      }`}
                    >
                      {titleCase(node)}
                    </span>
                  </React.Fragment>
                ))}
              </div>
              {d.plan_rationale && (
                <p className="text-sm italic text-muted-foreground">
                  {d.plan_rationale}
                </p>
              )}
              <div className="flex flex-wrap gap-1.5">
                <Badge variant="outline">
                  {d.clause_count} clauses
                </Badge>
                <Badge variant="outline" className="capitalize">
                  {d.sensitivity_tier}
                </Badge>
                <Badge
                  variant={d.external_providers_permitted ? "info" : "success"}
                >
                  external {d.external_providers_permitted ? "allowed" : "blocked"}
                </Badge>
              </div>
            </CardContent>
          </Card>

          {/* Verifier verdict */}
          <Card
            className={
              d.needs_human_review ? "border-warning/40" : undefined
            }
          >
            <CardHeader className="flex-row items-center justify-between">
              <CardTitle>Verifier</CardTitle>
              <div className="flex gap-1.5">
                <FaithfulnessBadge
                  ok={d.faithfulness_ok}
                  method={d.faithfulness_method}
                  unsupportedCount={(d.unsupported_claims ?? []).length}
                />
                {d.needs_human_review ? (
                  <Badge variant="warning">
                    <ShieldAlert /> needs review
                  </Badge>
                ) : (
                  <Badge variant="success">cleared</Badge>
                )}
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="rounded-lg border border-border bg-background p-3">
                <p className="whitespace-pre-wrap text-sm">{d.summary}</p>
              </div>
              {(d.unsupported_claims ?? []).length > 0 && (
                <div className="rounded-lg border border-warning/30 bg-warning/10 p-3 text-xs">
                  <p className="mb-1 font-medium text-warning">
                    Unsupported claims
                  </p>
                  {(d.unsupported_claims ?? []).map((c, i) => (
                    <p key={i} className="text-muted-foreground">
                      • {c}
                    </p>
                  ))}
                </div>
              )}
              {(d.invalid_citation_numbers ?? []).length > 0 && (
                <Badge variant="danger">
                  fabricated citations: {(d.invalid_citation_numbers ?? []).join(", ")}
                </Badge>
              )}
              {d.needs_human_review && (
                <Button variant="secondary" size="sm" asChild>
                  <Link href="/review">Open the review queue</Link>
                </Button>
              )}
            </CardContent>
          </Card>

          {/* Findings */}
          <div className="grid gap-6 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>
                  Risk findings ({(d.risk_findings ?? []).length})
                </CardTitle>
              </CardHeader>
              <CardContent>
                {(d.risk_findings ?? []).length === 0 ? (
                  <p className="text-sm text-muted-foreground">None flagged.</p>
                ) : (
                  <ul className="space-y-2">
                    {(d.risk_findings ?? []).map((f, i) => (
                      <li key={i} className="text-sm">
                        <Badge variant="warning">{f.term}</Badge>{" "}
                        <span className="text-xs text-subtle-foreground">
                          clause #{f.clause_id} · {f.source}
                        </span>
                        <p className="text-xs text-muted-foreground">
                          {f.explanation}
                        </p>
                      </li>
                    ))}
                  </ul>
                )}
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>
                  KG conflicts ({(d.kg_conflicts ?? []).length})
                </CardTitle>
              </CardHeader>
              <CardContent>
                {(d.kg_conflicts ?? []).length === 0 ? (
                  <p className="text-sm text-muted-foreground">
                    No candidate cross-document conflicts.
                  </p>
                ) : (
                  <ul className="space-y-2">
                    {(d.kg_conflicts ?? []).map((c, i) => (
                      <li
                        key={i}
                        className="rounded-lg border border-danger/30 bg-danger/[0.06] p-2.5 text-xs"
                      >
                        <Badge variant="danger">{c.term}</Badge>
                        <p className="mt-1 text-muted-foreground">
                          obligation (doc {c.obligation_document_id}) vs
                          prohibition (doc {c.prohibition_document_id})
                        </p>
                      </li>
                    ))}
                  </ul>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Trace */}
          <Card>
            <CardHeader>
              <CardTitle>Execution trace ({(d.trace ?? []).length} steps)</CardTitle>
            </CardHeader>
            <CardContent>
              <Accordion type="multiple" className="w-full">
                {(d.trace ?? []).map((step, i) => (
                  <AccordionItem key={i} value={`step-${i}`}>
                    <AccordionTrigger>
                      <span className="flex items-center gap-2">
                        <CircleDot className="size-3.5 text-primary" />
                        <span className="font-mono text-xs text-subtle-foreground">
                          {i + 1}
                        </span>
                        {titleCase(step.agent_name)}
                      </span>
                    </AccordionTrigger>
                    <AccordionContent>
                      <div className="space-y-1.5 pl-5 text-xs">
                        <p>
                          <span className="text-subtle-foreground">in: </span>
                          {step.input_summary}
                        </p>
                        <p>
                          <span className="text-subtle-foreground">out: </span>
                          {step.output_summary}
                        </p>
                      </div>
                    </AccordionContent>
                  </AccordionItem>
                ))}
              </Accordion>
            </CardContent>
          </Card>
        </>
      ) : null}
    </div>
  );
}
