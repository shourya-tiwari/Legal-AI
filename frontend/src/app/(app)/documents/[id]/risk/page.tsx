"use client";

import * as React from "react";
import dynamic from "next/dynamic";
import { useQuery } from "@tanstack/react-query";
import { ShieldAlert, ShieldCheck, Layers, Flame } from "lucide-react";
import { getRiskDashboard, riskScanDocument } from "@/lib/api";
import { qk } from "@/lib/query-keys";
import { useWorkspace } from "@/components/workspace/workspace-context";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Stat } from "@/components/ui/stat";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/ui/error-state";
import { EmptyState } from "@/components/ui/empty-state";
import { titleCase } from "@/lib/format";

const RiskRadar = dynamic(
  () => import("@/components/workspace/risk-radar").then((m) => m.RiskRadar),
  {
    ssr: false,
    loading: () => <Skeleton className="h-[340px] w-full" />,
  },
);

export default function RiskPage() {
  const { id } = useWorkspace();
  const [selected, setSelected] = React.useState<string | null>(null);

  const dash = useQuery({
    queryKey: qk.riskDashboard(id),
    queryFn: () => getRiskDashboard(id),
  });
  const scan = useQuery({
    queryKey: qk.riskScan(id),
    queryFn: () => riskScanDocument(id),
  });

  const categories = (dash.data?.categories ?? {}) as Record<string, number>;
  const clauseFindings = dash.data?.clause_findings ?? [];
  const total = dash.data?.total_flags ?? 0;
  const activeCategories = Object.entries(categories).filter(
    ([, v]) => v > 0,
  ).length;
  const topCategory = Object.entries(categories).sort(
    ([, a], [, b]) => b - a,
  )[0];

  const drill = selected
    ? clauseFindings.filter((f) => f.category === selected)
    : clauseFindings;

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-3">
        <Stat label="Total risk flags" value={total} icon={ShieldAlert} />
        <Stat
          label="Categories triggered"
          value={`${activeCategories}/8`}
          icon={Layers}
        />
        <Stat
          label="Highest-risk category"
          value={topCategory && topCategory[1] > 0 ? titleCase(topCategory[0]) : "—"}
          hint={topCategory && topCategory[1] > 0 ? `${topCategory[1]} flags` : ""}
          icon={Flame}
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_1.1fr]">
        <Card>
          <CardHeader>
            <CardTitle>Risk radar</CardTitle>
          </CardHeader>
          <CardContent>
            {dash.isLoading ? (
              <Skeleton className="h-[340px] w-full" />
            ) : dash.isError ? (
              <ErrorState error={dash.error} onRetry={() => dash.refetch()} />
            ) : (
              <RiskRadar
                categories={categories}
                onSelect={(c) => setSelected((s) => (s === c ? null : c))}
              />
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex-row items-center justify-between">
            <CardTitle>
              {selected ? `${titleCase(selected)} clauses` : "Clause-level flags"}
            </CardTitle>
            {selected && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setSelected(null)}
              >
                Clear filter
              </Button>
            )}
          </CardHeader>
          <CardContent>
            {dash.isLoading ? (
              <div className="space-y-2">
                <Skeleton className="h-12 w-full" />
                <Skeleton className="h-12 w-full" />
              </div>
            ) : drill.length === 0 ? (
              <EmptyState
                icon={ShieldCheck}
                title={selected ? "No flags in this category" : "No clause flags"}
                description="The keyword sweep found nothing high-risk."
              />
            ) : (
              <ul className="divide-y divide-border">
                {drill.map((f, i) => (
                  <li key={i} className="flex gap-3 py-3 text-sm">
                    <span className="shrink-0 font-mono text-xs text-subtle-foreground">
                      #{f.clause_id}
                    </span>
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-1.5">
                        <Badge variant="warning">{f.term}</Badge>
                        <Badge variant="outline">{titleCase(f.category)}</Badge>
                      </div>
                      <p className="mt-1 text-xs text-muted-foreground">
                        {f.explanation}
                      </p>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>AI + keyword scan</CardTitle>
        </CardHeader>
        <CardContent>
          {scan.isLoading ? (
            <Skeleton className="h-20 w-full" />
          ) : scan.isError ? (
            <ErrorState error={scan.error} onRetry={() => scan.refetch()} />
          ) : (scan.data?.flagged_clauses ?? []).length === 0 ? (
            <EmptyState
              icon={ShieldCheck}
              title="Nothing flagged"
              description={scan.data?.risk_summary}
            />
          ) : (
            <>
              <p className="mb-3 text-sm text-muted-foreground">
                {scan.data?.risk_summary}
              </p>
              <ul className="space-y-3">
                {(scan.data?.flagged_clauses ?? []).map((fc, i) => (
                  <li
                    key={i}
                    className="rounded-lg border border-border bg-surface p-3"
                  >
                    <p className="text-sm text-muted-foreground">{fc.clause}</p>
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      {(fc.keyword_flags ?? []).map((k, j) => (
                        <Badge key={`k${j}`} variant="warning">
                          {k.term}
                        </Badge>
                      ))}
                      {(fc.contextual_flags ?? []).map((k, j) => (
                        <Badge key={`c${j}`} variant="danger">
                          {k.term} (AI)
                        </Badge>
                      ))}
                    </div>
                  </li>
                ))}
              </ul>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
