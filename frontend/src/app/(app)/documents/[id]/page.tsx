"use client";

import Link from "next/link";
import { useMutation } from "@tanstack/react-query";
import { Wand2, Sparkles, ShieldAlert, ArrowRight } from "lucide-react";
import { analyzeDocument } from "@/lib/api";
import { useDocuments } from "@/lib/stores/documents";
import { useWorkspace } from "@/components/workspace/workspace-context";
import { TextViewer } from "@/components/workspace/text-viewer";
import { RewriteDialog } from "@/components/workspace/rewrite-dialog";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/ui/error-state";
import { FaithfulnessBadge } from "@/components/shared/faithfulness-badge";
import { titleCase } from "@/lib/format";
import { ConsistencyCard } from "@/components/workspace/consistency-card";

export default function OverviewPage() {
  const { id, document, sensitivity, blocks } = useWorkspace();
  const updateDoc = useDocuments((s) => s.update);

  const analyze = useMutation({
    mutationFn: () => analyzeDocument(id, { analysis_mode: "full" }),
    onSuccess: (r) =>
      updateDoc(id, {
        lastAnalyzedAt: new Date().toISOString(),
        needsReview: r.needs_human_review,
      }),
  });

  if (document.isLoading) {
    return (
      <div className="grid gap-6 lg:grid-cols-3">
        <Skeleton className="h-[520px] lg:col-span-2" />
        <Skeleton className="h-[520px]" />
      </div>
    );
  }
  if (!document.data) {
    return <ErrorState error={document.error} />;
  }
  const d = document.data;

  return (
    <div className="space-y-6">
      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader className="flex-row items-center justify-between">
            <CardTitle>Extracted text</CardTitle>
            <div className="flex gap-2">
              <RewriteDialog
                documentId={id}
                trigger={
                  <Button variant="secondary" size="sm">
                    <Wand2 /> Rewrite in plain English
                  </Button>
                }
              />
            </div>
          </CardHeader>
          <CardContent>
            <TextViewer text={d.full_text} />
          </CardContent>
        </Card>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Sensitivity</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              {sensitivity.isLoading ? (
                <Skeleton className="h-16 w-full" />
              ) : sensitivity.data ? (
                <>
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">Classified</span>
                    <Badge variant="outline" className="capitalize">
                      {sensitivity.data.source}
                    </Badge>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {sensitivity.data.rationale}
                  </p>
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">
                      External providers
                    </span>
                    <Badge
                      variant={
                        sensitivity.data.external_providers_permitted
                          ? "info"
                          : "success"
                      }
                    >
                      {sensitivity.data.external_providers_permitted
                        ? "permitted"
                        : "blocked"}
                    </Badge>
                  </div>
                </>
              ) : (
                <p className="text-muted-foreground">Unavailable.</p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex-row items-center justify-between">
              <CardTitle>Agent analysis</CardTitle>
              <Button variant="ghost" size="sm" asChild>
                <Link href={`/documents/${id}/agents`}>
                  Details <ArrowRight />
                </Link>
              </Button>
            </CardHeader>
            <CardContent className="space-y-3">
              {!analyze.data && !analyze.isPending && (
                <p className="text-sm text-muted-foreground">
                  Run the planner-driven pipeline for risk flags, KG conflicts, a
                  verified summary, and negotiation suggestions.
                </p>
              )}
              {analyze.isPending && (
                <div className="space-y-2">
                  <Skeleton className="h-4 w-full" />
                  <Skeleton className="h-4 w-3/4" />
                  <p className="text-xs text-muted-foreground">
                    Planning &amp; running agents…
                  </p>
                </div>
              )}
              {analyze.isError && (
                <ErrorState error={analyze.error} title="Analysis failed" />
              )}
              {analyze.data && (
                <div className="space-y-3">
                  <div className="flex flex-wrap gap-1.5">
                    <Badge variant="primary">
                      {(analyze.data.plan ?? []).join(" → ")}
                    </Badge>
                    <FaithfulnessBadge
                      ok={analyze.data.faithfulness_ok}
                      method={analyze.data.faithfulness_method}
                      unsupportedCount={
                        (analyze.data.unsupported_claims ?? []).length
                      }
                    />
                    {analyze.data.needs_human_review && (
                      <Badge variant="warning">
                        <ShieldAlert /> needs review
                      </Badge>
                    )}
                  </div>
                  <p className="line-clamp-4 text-sm text-muted-foreground">
                    {analyze.data.summary}
                  </p>
                  <p className="text-xs text-subtle-foreground">
                    {(analyze.data.risk_findings ?? []).length} risk ·{" "}
                    {(analyze.data.kg_conflicts ?? []).length} conflicts ·{" "}
                    {(analyze.data.negotiation_suggestions ?? []).length}{" "}
                    negotiation
                  </p>
                </div>
              )}
              <Button
                className="w-full"
                onClick={() => analyze.mutate()}
                loading={analyze.isPending}
                variant={analyze.data ? "secondary" : "primary"}
              >
                <Sparkles />
                {analyze.data ? "Re-run analysis" : "Run full analysis"}
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>

      <Card>
        <CardHeader className="flex-row items-center justify-between">
          <CardTitle>Clauses ({blocks.length})</CardTitle>
          <Button variant="ghost" size="sm" asChild>
            <Link href={`/documents/${id}/clauses`}>
              Structured analysis <ArrowRight />
            </Link>
          </Button>
        </CardHeader>
        <CardContent>
          <ul className="divide-y divide-border">
            {blocks.slice(0, 15).map((b) => (
              <li key={b.id} className="flex items-start gap-3 py-3">
                <span className="mt-0.5 shrink-0 font-mono text-xs text-subtle-foreground">
                  {b.id}
                </span>
                <p className="line-clamp-2 flex-1 text-sm text-muted-foreground">
                  {b.text}
                </p>
                {b.type && (
                  <Badge variant="outline" className="shrink-0">
                    {titleCase(b.type)}
                  </Badge>
                )}
              </li>
            ))}
          </ul>
          {blocks.length > 15 && (
            <p className="pt-3 text-xs text-subtle-foreground">
              + {blocks.length - 15} more in the Clauses tab.
            </p>
          )}
        </CardContent>
      </Card>

      <ConsistencyCard documentId={id} />
    </div>
  );
}
