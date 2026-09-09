"use client";

import * as React from "react";
import { useParams } from "next/navigation";
import { useQuery, useMutation } from "@tanstack/react-query";
import {
  Download,
  FileText,
  AlertTriangle,
  Workflow,
  Sparkles,
  ShieldAlert,
} from "lucide-react";
import {
  getDocument,
  getSensitivity,
  originalFileUrl,
  analyzeDocument,
  type DocumentQuality,
} from "@/lib/api";
import { qk } from "@/lib/query-keys";
import { useDocuments } from "@/lib/stores/documents";
import { PageHeader, PageBody } from "@/components/layout/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/ui/error-state";
import { SensitivityBadge } from "@/components/shared/sensitivity-badge";
import { FaithfulnessBadge } from "@/components/shared/faithfulness-badge";
import { bytes, relativeTime, titleCase } from "@/lib/format";

export default function WorkspacePage() {
  const params = useParams<{ id: string }>();
  const id = Number(params.id);
  const updateDoc = useDocuments((s) => s.update);

  const doc = useQuery({
    queryKey: qk.document(id),
    queryFn: () => getDocument(id),
    enabled: Number.isFinite(id),
  });
  const sens = useQuery({
    queryKey: qk.sensitivity(id),
    queryFn: () => getSensitivity(id),
    enabled: Number.isFinite(id),
  });

  const analyze = useMutation({
    mutationFn: () => analyzeDocument(id, { analysis_mode: "full" }),
    onSuccess: (r) =>
      updateDoc(id, {
        lastAnalyzedAt: new Date().toISOString(),
        needsReview: r.needs_human_review,
      }),
  });

  if (doc.isLoading) {
    return (
      <PageBody className="space-y-4">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-64 w-full" />
      </PageBody>
    );
  }
  if (doc.isError || !doc.data) {
    return (
      <PageBody>
        <ErrorState error={doc.error} title="Could not load this document" />
      </PageBody>
    );
  }

  const d = doc.data;
  const quality = d.quality as DocumentQuality | null | undefined;
  const blocks = (d.blocks ?? []) as { id: number | string; text: string; type?: string; page?: number }[];

  return (
    <>
      <PageHeader
        title={d.filename}
        breadcrumbs={[
          { label: "Documents", href: "/documents" },
          { label: d.filename },
        ]}
        description={
          <span className="flex flex-wrap items-center gap-2">
            <span>{blocks.length} clauses</span>
            <span>·</span>
            <span>{d.content_type ?? "unknown type"}</span>
            {d.created_at && (
              <>
                <span>·</span>
                <span>uploaded {relativeTime(d.created_at)}</span>
              </>
            )}
          </span>
        }
        actions={
          <>
            <SensitivityBadge
              tier={d.sensitivity_tier}
              externalAllowed={sens.data?.external_providers_permitted}
            />
            {d.original_available && (
              <Button variant="secondary" size="sm" asChild>
                <a href={originalFileUrl(id)}>
                  <Download /> Original ({bytes(d.original_size)})
                </a>
              </Button>
            )}
          </>
        }
      />

      <PageBody className="space-y-6">
        {quality && quality.low_quality_pages.length > 0 && (
          <Alert variant="warning">
            <AlertTriangle />
            <div>
              <AlertTitle>Scan quality warning</AlertTitle>
              <AlertDescription>
                {quality.low_quality_pages.length} of {quality.pages_assessed}{" "}
                page(s) flagged low-quality (pages{" "}
                {quality.low_quality_pages.join(", ")}). OCR extraction may be
                less reliable there.
                {(quality.pages_with_redactions?.length ?? 0) > 0 && (
                  <>
                    {" "}
                    Redaction boxes detected on page(s){" "}
                    {quality.pages_with_redactions!.join(", ")}.
                  </>
                )}
              </AlertDescription>
            </div>
          </Alert>
        )}

        <div className="grid gap-6 lg:grid-cols-3">
          {/* Full text */}
          <Card className="lg:col-span-2">
            <CardHeader className="flex-row items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                <FileText className="size-4" /> Extracted text
              </CardTitle>
              <Badge variant="outline">
                {d.full_text.length.toLocaleString()} chars
              </Badge>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-[420px] rounded-lg border border-border bg-background">
                <pre className="whitespace-pre-wrap p-4 font-mono text-[13px] leading-relaxed text-muted-foreground">
                  {d.full_text || "No text extracted."}
                </pre>
              </ScrollArea>
            </CardContent>
          </Card>

          {/* Sidebar: sensitivity + analysis */}
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Sensitivity</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                {sens.isLoading ? (
                  <Skeleton className="h-16 w-full" />
                ) : sens.data ? (
                  <>
                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground">Source</span>
                      <Badge variant="outline" className="capitalize">
                        {sens.data.source}
                      </Badge>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      {sens.data.rationale}
                    </p>
                    {(sens.data.signals ?? []).length > 0 && (
                      <div className="flex flex-wrap gap-1.5">
                        {(sens.data.signals ?? []).slice(0, 5).map((s, i) => (
                          <Badge key={i} variant="default" className="text-[10px]">
                            {(s as { phrase?: string; category?: string }).category ??
                              (s as { phrase?: string }).phrase ??
                              "signal"}
                          </Badge>
                        ))}
                      </div>
                    )}
                  </>
                ) : (
                  <p className="text-muted-foreground">Unavailable.</p>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Workflow className="size-4" /> Agent analysis
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {!analyze.data && !analyze.isPending && (
                  <p className="text-sm text-muted-foreground">
                    Run the planner-driven pipeline: risk flags, KG conflicts, a
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
                        plan: {(analyze.data.plan ?? []).join(" → ")}
                      </Badge>
                      <FaithfulnessBadge
                        ok={analyze.data.faithfulness_ok}
                        method={analyze.data.faithfulness_method}
                        unsupportedCount={(analyze.data.unsupported_claims ?? []).length}
                      />
                      {analyze.data.needs_human_review && (
                        <Badge variant="warning">
                          <ShieldAlert /> needs review
                        </Badge>
                      )}
                    </div>
                    {analyze.data.plan_rationale && (
                      <p className="text-xs italic text-subtle-foreground">
                        {analyze.data.plan_rationale}
                      </p>
                    )}
                    <div className="rounded-lg border border-border bg-background p-3">
                      <p className="whitespace-pre-wrap text-sm text-muted-foreground">
                        {analyze.data.summary}
                      </p>
                    </div>
                    {(analyze.data.risk_findings ?? []).length > 0 && (
                      <p className="text-xs text-muted-foreground">
                        {(analyze.data.risk_findings ?? []).length} risk finding(s) ·{" "}
                        {(analyze.data.kg_conflicts ?? []).length} KG conflict(s) ·{" "}
                        {(analyze.data.negotiation_suggestions ?? []).length} negotiation
                        suggestion(s)
                      </p>
                    )}
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

        {/* Clause preview */}
        <Card>
          <CardHeader>
            <CardTitle>Clauses ({blocks.length})</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="divide-y divide-border">
              {blocks.slice(0, 12).map((b) => (
                <li key={b.id} className="flex gap-3 py-3">
                  <span className="font-mono text-xs text-subtle-foreground">
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
            {blocks.length > 12 && (
              <p className="pt-3 text-xs text-subtle-foreground">
                + {blocks.length - 12} more — full clause analysis lands with the
                Clauses tab.
              </p>
            )}
          </CardContent>
        </Card>
      </PageBody>
    </>
  );
}
