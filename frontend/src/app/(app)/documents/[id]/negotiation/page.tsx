"use client";

import * as React from "react";
import Link from "next/link";
import { GitCompareArrows, Check, X, Download, Settings } from "lucide-react";
import { toast } from "sonner";
import { useWorkspace } from "@/components/workspace/workspace-context";
import { useAnalysis } from "@/components/workspace/use-analysis";
import { RunAnalysisCta } from "@/components/workspace/run-analysis-cta";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { titleCase, pct } from "@/lib/format";
import { cn } from "@/lib/utils";

type Decision = "pending" | "accepted" | "rejected";

export default function NegotiationPage() {
  const { id, document } = useWorkspace();
  const analysis = useAnalysis(id, "full", false);
  const [decisions, setDecisions] = React.useState<Record<number, Decision>>({});

  const suggestions = analysis.data?.negotiation_suggestions ?? [];

  const exportRedline = () => {
    const lines = suggestions
      .filter((s) => decisions[s.clause_id] !== "rejected")
      .map(
        (s) =>
          `## Clause ${s.clause_id} — ${titleCase(s.clause_type)}\n` +
          `Status: ${decisions[s.clause_id] ?? "pending review"}\n\n` +
          `Rationale: ${s.rationale}\n\n` +
          "```diff\n" +
          (s.diff_lines ?? []).join("\n") +
          "\n```\n",
      );
    const blob = new Blob(
      [
        `# Redline suggestions — ${document.data?.filename ?? "document"}\n\n` +
          lines.join("\n---\n\n"),
      ],
      { type: "text/markdown" },
    );
    const url = URL.createObjectURL(blob);
    const a = window.document.createElement("a");
    a.href = url;
    a.download = `redline-${id}.md`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success("Redline exported");
  };

  return (
    <div className="space-y-6">
      {!analysis.hasRun ? (
        <RunAnalysisCta
          title="Compare clauses to your playbook"
          description="The Negotiation agent compares each clause against your organisation's preferred language and produces a redline for every deviation."
          isPending={analysis.isPending}
          isError={analysis.isError}
          error={analysis.error}
          onRun={() => analysis.run()}
        />
      ) : suggestions.length === 0 ? (
        <EmptyState
          icon={GitCompareArrows}
          title="No suggestions"
          description="Either every covered clause already matches your preferred language, or your organisation hasn't configured any negotiation preferences yet."
          action={
            <Button variant="secondary" asChild>
              <Link href="/settings">
                <Settings /> Configure preferences
              </Link>
            </Button>
          }
        />
      ) : (
        <>
          <div className="flex items-center justify-between">
            <p className="text-sm text-muted-foreground">
              {suggestions.length} deviation
              {suggestions.length === 1 ? "" : "s"} from your playbook · every
              suggestion is pending review, nothing is auto-applied
            </p>
            <Button variant="secondary" size="sm" onClick={exportRedline}>
              <Download /> Export redline
            </Button>
          </div>

          {suggestions.map((s) => {
            const decision = decisions[s.clause_id] ?? "pending";
            return (
              <Card key={s.clause_id}>
                <CardHeader className="flex-row items-start justify-between gap-3">
                  <div className="space-y-1">
                    <CardTitle className="flex items-center gap-2">
                      Clause #{s.clause_id}
                      <Badge variant="primary">{titleCase(s.clause_type)}</Badge>
                    </CardTitle>
                    <p className="text-xs text-subtle-foreground">
                      {pct(s.similarity)} textual similarity · {s.status}
                    </p>
                  </div>
                  <div className="flex gap-1.5">
                    <Button
                      variant={decision === "accepted" ? "primary" : "outline"}
                      size="sm"
                      onClick={() =>
                        setDecisions((d) => ({
                          ...d,
                          [s.clause_id]:
                            decision === "accepted" ? "pending" : "accepted",
                        }))
                      }
                    >
                      <Check /> Accept
                    </Button>
                    <Button
                      variant={decision === "rejected" ? "danger" : "outline"}
                      size="sm"
                      onClick={() =>
                        setDecisions((d) => ({
                          ...d,
                          [s.clause_id]:
                            decision === "rejected" ? "pending" : "rejected",
                        }))
                      }
                    >
                      <X /> Reject
                    </Button>
                  </div>
                </CardHeader>
                <CardContent className="space-y-3">
                  <p className="text-sm text-muted-foreground">{s.rationale}</p>
                  <div className="grid gap-3 md:grid-cols-2">
                    <div>
                      <p className="mb-1 text-xs font-medium text-subtle-foreground">
                        Current language
                      </p>
                      <div className="rounded-lg border border-danger/30 bg-danger/[0.05] p-3 text-sm text-muted-foreground">
                        {s.current_language}
                      </div>
                    </div>
                    <div>
                      <p className="mb-1 text-xs font-medium text-subtle-foreground">
                        Preferred language
                      </p>
                      <div className="rounded-lg border border-success/30 bg-success/[0.05] p-3 text-sm text-muted-foreground">
                        {s.suggested_language}
                      </div>
                    </div>
                  </div>
                  {(s.diff_lines ?? []).length > 0 && (
                    <pre className="overflow-x-auto rounded-lg bg-background p-3 font-mono text-xs leading-relaxed">
                      {(s.diff_lines ?? []).map((line, i) => (
                        <div
                          key={i}
                          className={cn(
                            line.startsWith("+") && "text-success",
                            line.startsWith("-") && "text-danger",
                            line.startsWith("?") && "text-subtle-foreground",
                          )}
                        >
                          {line}
                        </div>
                      ))}
                    </pre>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </>
      )}
    </div>
  );
}
