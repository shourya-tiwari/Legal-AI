"use client";

import { useQuery } from "@tanstack/react-query";
import { Cpu, Wifi, WifiOff, ExternalLink } from "lucide-react";
import { getModelsStatus } from "@/lib/api";
import { qk } from "@/lib/query-keys";
import { PageHeader, PageBody } from "@/components/layout/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ErrorState } from "@/components/ui/error-state";
import { HostingClassBadge } from "@/components/shared/hosting-class-badge";
import { CardSkeleton } from "@/components/shared/loaders";
import { ms } from "@/lib/format";

export default function ModelsPage() {
  const q = useQuery({ queryKey: qk.modelsStatus, queryFn: getModelsStatus });

  return (
    <>
      <PageHeader
        title="Model Router"
        description="Every AI call is routed by task and sensitivity tier through a declarative policy. Providers are classified by where they run: A (deterministic/CPU), B (self-hosted neural), C (external API)."
      />
      <PageBody className="space-y-6">
        {q.isLoading ? (
          <div className="grid gap-4 md:grid-cols-2">
            <CardSkeleton />
            <CardSkeleton />
            <CardSkeleton />
            <CardSkeleton />
          </div>
        ) : q.isError ? (
          <ErrorState error={q.error} onRetry={() => q.refetch()} />
        ) : (
          q.data && (
            <>
              <div className="flex flex-wrap gap-3">
                <Badge variant="outline">
                  policy v{q.data.policy_version}
                </Badge>
                <Badge
                  variant={
                    q.data.external_providers_enabled ? "info" : "success"
                  }
                >
                  external providers{" "}
                  {q.data.external_providers_enabled ? "enabled" : "off"}
                </Badge>
                {q.data.strict_local_only && (
                  <Badge variant="success">strict local only</Badge>
                )}
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                {(q.data.providers ?? []).map((p) => (
                  <Card key={p.name}>
                    <CardHeader className="flex-row items-start justify-between gap-3">
                      <div className="min-w-0 space-y-1">
                        <CardTitle className="flex items-center gap-2 font-mono text-[13px]">
                          <Cpu className="size-4 text-muted-foreground" />
                          {p.name}
                        </CardTitle>
                        {(p.models ?? []).length > 0 && (
                          <p className="truncate text-xs text-subtle-foreground">
                            {(p.models ?? []).join(", ")}
                          </p>
                        )}
                      </div>
                      <HostingClassBadge hostingClass={p.hosting_class} />
                    </CardHeader>
                    <CardContent className="space-y-3">
                      <div className="flex flex-wrap gap-1.5">
                        {(p.capabilities ?? []).map((c) => (
                          <Badge key={c} variant="default">
                            {c}
                          </Badge>
                        ))}
                      </div>
                      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs">
                        <span
                          className={`flex items-center gap-1.5 ${
                            p.available ? "text-success" : "text-subtle-foreground"
                          }`}
                        >
                          {p.available ? (
                            <Wifi className="size-3.5" />
                          ) : (
                            <WifiOff className="size-3.5" />
                          )}
                          {p.available ? "reachable" : "not configured"}
                        </span>
                        {p.leaves_perimeter && (
                          <span className="flex items-center gap-1.5 text-warning">
                            <ExternalLink className="size-3.5" />
                            leaves perimeter
                          </span>
                        )}
                        {p.recent_call_count > 0 && (
                          <span className="text-muted-foreground">
                            {ms(p.recent_avg_latency_ms)} avg ·{" "}
                            {p.recent_call_count} recent calls
                          </span>
                        )}
                      </div>
                      {p.note && (
                        <p className="text-xs text-subtle-foreground">{p.note}</p>
                      )}
                    </CardContent>
                  </Card>
                ))}
              </div>
            </>
          )
        )}
      </PageBody>
    </>
  );
}
