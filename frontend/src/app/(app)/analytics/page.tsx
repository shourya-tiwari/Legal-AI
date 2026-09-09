"use client";

import { useQuery } from "@tanstack/react-query";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  ResponsiveContainer,
  Cell,
  Tooltip as RTooltip,
} from "recharts";
import { Activity, Cpu, ShieldAlert, FileText, ExternalLink } from "lucide-react";
import {
  getModelsStatus,
  getEvalRuns,
  getEgressLog,
  getReviewQueue,
} from "@/lib/api";
import { qk } from "@/lib/query-keys";
import { useDocuments } from "@/lib/stores/documents";
import { useChat } from "@/lib/stores/chat";
import { PageHeader, PageBody } from "@/components/layout/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Stat } from "@/components/ui/stat";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { HostingClassBadge } from "@/components/shared/hosting-class-badge";
import { ms, pct, relativeTime } from "@/lib/format";

export default function AnalyticsPage() {
  const docs = useDocuments((s) => s.docs);
  const conversations = useChat((s) => s.conversations);

  const models = useQuery({ queryKey: qk.modelsStatus, queryFn: getModelsStatus });
  const evals = useQuery({ queryKey: qk.evalRuns, queryFn: getEvalRuns });
  const egress = useQuery({
    queryKey: qk.egress(100),
    queryFn: () => getEgressLog(100),
  });
  const review = useQuery({
    queryKey: qk.reviewQueue(true),
    queryFn: () => getReviewQueue(true),
  });

  const providers = (models.data?.providers ?? []).filter(
    (p) => p.recent_call_count > 0,
  );
  const latencyData = providers.map((p) => ({
    name: p.name,
    ms: p.recent_avg_latency_ms ?? 0,
    class: p.hosting_class,
  }));

  const egressEntries = egress.data?.entries ?? [];
  const egressByProvider = egressEntries.reduce<Record<string, number>>(
    (acc, e) => {
      acc[e.provider] = (acc[e.provider] ?? 0) + 1;
      return acc;
    },
    {},
  );
  const redactedTotal = egressEntries.reduce(
    (sum, e) =>
      sum +
      Object.values(
        (e.redacted_categories ?? {}) as Record<string, number>,
      ).reduce((a, b) => a + b, 0),
    0,
  );

  const reviewItems = review.data?.items ?? [];
  const totalMessages = conversations.reduce(
    (s, c) => s + c.messages.length,
    0,
  );
  const analysesRun = docs.filter((d) => d.lastAnalyzedAt).length;

  return (
    <>
      <PageHeader
        title="Analytics"
        description="Cross-cutting signals from real sources: model latency, evaluation pass rates, Class-C egress, the review queue, and your local activity."
      />
      <PageBody className="space-y-6">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Stat
            label="Documents analysed"
            value={`${analysesRun}/${docs.length}`}
            hint="this browser"
            icon={FileText}
          />
          <Stat
            label="Assistant messages"
            value={totalMessages}
            hint={`${conversations.length} conversations`}
            icon={Activity}
          />
          <Stat
            label="Class-C dispatches"
            value={egress.isLoading ? "—" : egressEntries.length}
            hint={`${redactedTotal} identifiers redacted`}
            icon={ExternalLink}
          />
          <Stat
            label="Flagged analyses"
            value={reviewItems.length}
            hint={`${reviewItems.filter((i) => i.reviewed).length} resolved`}
            icon={ShieldAlert}
          />
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Provider latency</CardTitle>
            </CardHeader>
            <CardContent>
              {models.isLoading ? (
                <Skeleton className="h-56 w-full" />
              ) : latencyData.length === 0 ? (
                <EmptyState
                  icon={Cpu}
                  title="No recorded calls yet"
                  description="Latency is aggregated from model_calls rows. Run an analysis to populate it."
                />
              ) : (
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart
                    data={latencyData}
                    layout="vertical"
                    margin={{ left: 12, right: 12 }}
                  >
                    <XAxis
                      type="number"
                      tick={{ fill: "var(--color-subtle-foreground)", fontSize: 10 }}
                      stroke="var(--color-border)"
                    />
                    <YAxis
                      type="category"
                      dataKey="name"
                      width={110}
                      tick={{ fill: "var(--color-muted-foreground)", fontSize: 10 }}
                      stroke="var(--color-border)"
                    />
                    <RTooltip
                      cursor={{ fill: "var(--color-muted)" }}
                      contentStyle={{
                        background: "var(--color-overlay)",
                        border: "1px solid var(--color-border)",
                        borderRadius: 8,
                        fontSize: 12,
                      }}
                      formatter={(v) => [ms(Number(v)), "avg latency"]}
                    />
                    <Bar dataKey="ms" radius={4}>
                      {latencyData.map((d, i) => (
                        <Cell
                          key={i}
                          fill={
                            d.class === "C"
                              ? "var(--color-warning)"
                              : d.class === "B"
                                ? "var(--color-info)"
                                : "var(--color-primary)"
                          }
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Class-C egress by provider</CardTitle>
            </CardHeader>
            <CardContent>
              {egress.isLoading ? (
                <Skeleton className="h-56 w-full" />
              ) : Object.keys(egressByProvider).length === 0 ? (
                <EmptyState
                  icon={ExternalLink}
                  title="Nothing has left the perimeter"
                  description="No request has been dispatched to an external provider."
                />
              ) : (
                <ul className="space-y-3">
                  {Object.entries(egressByProvider).map(([prov, count]) => {
                    const maxc = Math.max(...Object.values(egressByProvider));
                    return (
                      <li key={prov}>
                        <div className="flex items-center justify-between text-sm">
                          <span className="font-mono text-xs">{prov}</span>
                          <span className="text-muted-foreground">{count}</span>
                        </div>
                        <div className="mt-1 h-2 overflow-hidden rounded-full bg-muted">
                          <div
                            className="h-full rounded-full bg-warning"
                            style={{ width: `${(count / maxc) * 100}%` }}
                          />
                        </div>
                      </li>
                    );
                  })}
                </ul>
              )}
            </CardContent>
          </Card>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Evaluation pass rate by task</CardTitle>
          </CardHeader>
          <CardContent>
            {evals.isLoading ? (
              <Skeleton className="h-24 w-full" />
            ) : (
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {[
                  ...new Set(
                    (evals.data?.runs ?? [])
                      .filter((r) => r.passed != null)
                      .map((r) => r.task),
                  ),
                ].map((task) => {
                  const forTask = (evals.data?.runs ?? []).filter(
                    (r) => r.task === task && r.passed != null,
                  );
                  const p = forTask.filter((r) => r.passed).length;
                  return (
                    <div
                      key={task}
                      className="rounded-lg border border-border bg-surface p-3"
                    >
                      <p className="font-mono text-xs">{task}</p>
                      <p className="mt-1 text-lg font-semibold">
                        {pct(p / forTask.length, 0)}
                      </p>
                      <p className="text-xs text-subtle-foreground">
                        {p}/{forTask.length} providers pass
                      </p>
                    </div>
                  );
                })}
                {(evals.data?.runs ?? []).filter((r) => r.passed != null)
                  .length === 0 && (
                  <p className="text-sm text-muted-foreground">
                    No gated eval runs recorded.
                  </p>
                )}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Recent Class-C dispatches</CardTitle>
          </CardHeader>
          <CardContent>
            {egressEntries.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                No external dispatches recorded.
              </p>
            ) : (
              <ul className="divide-y divide-border text-sm">
                {egressEntries.slice(0, 8).map((e) => (
                  <li
                    key={e.id}
                    className="flex flex-wrap items-center gap-2 py-2.5"
                  >
                    <Badge variant="outline" className="font-mono text-[10px]">
                      {e.task}
                    </Badge>
                    <span className="text-muted-foreground">
                      → {e.provider} ({e.model})
                    </span>
                    {e.sensitivity && (
                      <HostingClassBadge hostingClass="C" />
                    )}
                    <span className="ml-auto text-xs text-subtle-foreground">
                      {relativeTime(e.created_at)}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </PageBody>
    </>
  );
}
