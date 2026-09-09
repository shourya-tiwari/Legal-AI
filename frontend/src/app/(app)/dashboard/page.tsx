"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import {
  Upload,
  Sparkles,
  FileText,
  ClipboardCheck,
  Cpu,
  ArrowRight,
  Activity,
  ShieldAlert,
} from "lucide-react";
import {
  getModelsStatus,
  getReviewQueue,
  getEvalRuns,
  getHealth,
} from "@/lib/api";
import { qk } from "@/lib/query-keys";
import { useDocuments } from "@/lib/stores/documents";
import { PageHeader, PageBody } from "@/components/layout/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Stat } from "@/components/ui/stat";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { SensitivityBadge } from "@/components/shared/sensitivity-badge";
import { HostingClassBadge } from "@/components/shared/hosting-class-badge";
import { StatGridSkeleton } from "@/components/shared/loaders";
import { DashboardOnboarding } from "@/components/dashboard/onboarding";
import { relativeTime, pct } from "@/lib/format";

export default function DashboardPage() {
  const docs = useDocuments((s) => s.docs);
  const empty = docs.length === 0;

  const health = useQuery({
    queryKey: qk.health,
    queryFn: getHealth,
    retry: false,
  });
  const models = useQuery({
    queryKey: qk.modelsStatus,
    queryFn: getModelsStatus,
  });
  const review = useQuery({
    queryKey: qk.reviewQueue(false),
    queryFn: () => getReviewQueue(false),
  });
  const evals = useQuery({ queryKey: qk.evalRuns, queryFn: getEvalRuns });

  const providers = models.data?.providers ?? [];
  const evalRuns = evals.data?.runs ?? [];
  const reviewItems = review.data?.items ?? [];
  const availableProviders = providers.filter((p) => p.available).length;
  const totalProviders = providers.length;
  const passedGates = evalRuns.filter((r) => r.passed === true).length;
  const gatedRuns = evalRuns.filter((r) => r.passed != null).length;

  const modelRouterCard = (
    <Card>
      <CardHeader>
        <CardTitle>Model Router</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {models.isLoading ? (
          <div className="space-y-2">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-3/4" />
          </div>
        ) : models.isError ? (
          <p className="text-sm text-muted-foreground">
            Router status unavailable.
          </p>
        ) : (
          <>
            <div className="flex flex-wrap gap-1.5">
              {[...new Set(providers.map((p) => p.hosting_class))]
                .sort()
                .map((c) => (
                  <HostingClassBadge key={c} hostingClass={c} />
                ))}
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Policy version</span>
              <span className="font-mono">v{models.data!.policy_version}</span>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">External providers</span>
              <Badge
                variant={
                  models.data!.external_providers_enabled ? "info" : "success"
                }
              >
                {models.data!.external_providers_enabled
                  ? "enabled"
                  : "off (local only)"}
              </Badge>
            </div>
            <Button variant="ghost" size="sm" asChild className="w-full">
              <Link href="/models">
                Open Model Router <ArrowRight />
              </Link>
            </Button>
          </>
        )}
      </CardContent>
    </Card>
  );

  const backendCard = (
    <Card>
      <CardHeader>
        <CardTitle>Backend</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex items-center gap-2 text-sm">
          <span
            className={`size-2 rounded-full ${
              health.isLoading
                ? "bg-warning"
                : health.isError
                  ? "bg-danger"
                  : "bg-success"
            }`}
          />
          <span className="text-muted-foreground">
            {health.isLoading
              ? "Checking…"
              : health.isError
                ? "Unreachable"
                : "Reachable"}
          </span>
        </div>
        <Button variant="ghost" size="sm" asChild className="mt-3 w-full">
          <Link href="/analytics">
            Platform analytics <ArrowRight />
          </Link>
        </Button>
      </CardContent>
    </Card>
  );

  const reviewCard = reviewItems.length > 0 && (
    <Card>
      <CardHeader className="flex-row items-center justify-between">
        <CardTitle className="flex items-center gap-2">
          <ShieldAlert className="size-4 text-warning" />
          Awaiting human review
        </CardTitle>
        <Button variant="ghost" size="sm" asChild>
          <Link href="/review">
            Review queue <ArrowRight />
          </Link>
        </Button>
      </CardHeader>
      <CardContent>
        <ul className="divide-y divide-border">
          {reviewItems.slice(0, 4).map((item) => (
            <li key={item.id} className="flex items-center gap-3 py-3 text-sm">
              <Link
                href={`/documents/${item.document_id}`}
                className="font-medium hover:text-primary"
              >
                {item.document_filename}
              </Link>
              <span className="truncate text-muted-foreground">
                {item.summary}
              </span>
              <Badge
                variant={item.faithfulness_ok ? "success" : "warning"}
                className="ml-auto shrink-0"
              >
                {item.faithfulness_ok
                  ? "faithful"
                  : `${(item.unsupported_claims ?? []).length} unsupported`}
              </Badge>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );

  const evalCard = gatedRuns > 0 && (
    <Card>
      <CardHeader className="flex-row items-center justify-between">
        <CardTitle>Latest evaluation gates</CardTitle>
        <Button variant="ghost" size="sm" asChild>
          <Link href="/evaluation">
            Evaluation <ArrowRight />
          </Link>
        </Button>
      </CardHeader>
      <CardContent>
        <ul className="space-y-2">
          {evalRuns
            .filter((r) => r.passed != null)
            .slice(0, 5)
            .map((r, i) => (
              <li
                key={i}
                className="flex items-center justify-between gap-3 text-sm"
              >
                <span className="font-mono text-xs">{r.task}</span>
                <span className="text-muted-foreground">
                  {r.provider} · {r.metric} {pct(r.score, 1)}
                  {r.baseline_score != null && ` vs ${pct(r.baseline_score, 1)}`}
                </span>
                <Badge
                  variant={r.passed ? "success" : "danger"}
                  className="shrink-0"
                >
                  {r.passed ? "pass" : "fail"}
                </Badge>
              </li>
            ))}
        </ul>
      </CardContent>
    </Card>
  );

  return (
    <>
      <PageHeader
        title="Dashboard"
        description={
          empty
            ? "Get started — upload a contract or open the sample NDA."
            : "Your Legal-AI workspace at a glance."
        }
        actions={
          <>
            <Button variant="secondary" asChild>
              <Link href="/assistant">
                <Sparkles /> Assistant
              </Link>
            </Button>
            <Button asChild>
              <Link href="/documents/upload">
                <Upload /> Upload
              </Link>
            </Button>
          </>
        }
      />
      <PageBody className="space-y-6">
        {empty ? (
          <>
            <DashboardOnboarding />
            <div>
              <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-subtle-foreground">
                Platform status
              </h3>
              <div className="grid gap-6 sm:grid-cols-2">
                {modelRouterCard}
                {backendCard}
              </div>
            </div>
            {reviewCard}
            {evalCard}
          </>
        ) : (
          <>
            {models.isLoading ? (
              <StatGridSkeleton />
            ) : (
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <Stat
                  label="Documents in library"
                  value={docs.length}
                  hint="uploaded from this browser"
                  icon={FileText}
                />
                <Stat
                  label="Needs human review"
                  value={reviewItems.length || "—"}
                  hint={
                    reviewItems.length
                      ? "unresolved analyses"
                      : "queue is clear"
                  }
                  icon={ClipboardCheck}
                />
                <Stat
                  label="Model providers"
                  value={
                    totalProviders
                      ? `${availableProviders}/${totalProviders}`
                      : "—"
                  }
                  hint="reachable now"
                  icon={Cpu}
                />
                <Stat
                  label="Cutover gates passed"
                  value={gatedRuns ? `${passedGates}/${gatedRuns}` : "—"}
                  hint="self-hosted ≥ baseline"
                  icon={Activity}
                />
              </div>
            )}

            <div className="grid gap-6 lg:grid-cols-3">
              <Card className="lg:col-span-2">
                <CardHeader className="flex-row items-center justify-between">
                  <CardTitle>Recent documents</CardTitle>
                  <Button variant="ghost" size="sm" asChild>
                    <Link href="/documents">
                      All documents <ArrowRight />
                    </Link>
                  </Button>
                </CardHeader>
                <CardContent>
                  <ul className="divide-y divide-border">
                    {docs.slice(0, 6).map((d) => (
                      <li key={d.id}>
                        <Link
                          href={`/documents/${d.id}`}
                          className="flex items-center gap-3 py-3 transition-colors hover:text-primary"
                        >
                          <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-muted text-muted-foreground">
                            <FileText className="size-4" />
                          </div>
                          <div className="min-w-0 flex-1">
                            <p className="truncate text-sm font-medium">
                              {d.filename}
                            </p>
                            <p className="text-xs text-muted-foreground">
                              {d.clauseCount} clauses · {relativeTime(d.uploadedAt)}
                            </p>
                          </div>
                          <SensitivityBadge tier={d.sensitivityTier} />
                        </Link>
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>

              <div className="space-y-6">
                {modelRouterCard}
                {backendCard}
              </div>
            </div>

            {reviewCard}
            {evalCard}
          </>
        )}
      </PageBody>
    </>
  );
}
