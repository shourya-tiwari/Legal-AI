"use client";

import { useQuery } from "@tanstack/react-query";
import { Cpu, KeyRound, Database, Network } from "lucide-react";
import { getHealth, getModelsStatus } from "@/lib/api";
import { qk } from "@/lib/query-keys";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { CodeBlock } from "@/components/shared/code-block";

function HealthDot({ state }: { state: "ok" | "warn" | "down" | "loading" }) {
  const cls =
    state === "ok"
      ? "bg-success"
      : state === "warn"
        ? "bg-warning"
        : state === "down"
          ? "bg-danger"
          : "bg-muted-foreground animate-pulse";
  return <span className={`size-2 rounded-full ${cls}`} />;
}

export default function AdminOverviewPage() {
  const health = useQuery({ queryKey: qk.health, queryFn: getHealth, retry: false });
  const models = useQuery({ queryKey: qk.modelsStatus, queryFn: getModelsStatus });

  const providerHealth = models.data?.providers ?? [];

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card className="p-4">
          <div className="flex items-center gap-2">
            <HealthDot
              state={
                health.isLoading ? "loading" : health.isError ? "down" : "ok"
              }
            />
            <p className="text-sm font-medium">API</p>
          </div>
          <p className="mt-1 text-xs text-muted-foreground">
            {health.isLoading
              ? "checking…"
              : health.isError
                ? "unreachable"
                : "reachable"}
          </p>
        </Card>
        <Card className="p-4">
          <div className="flex items-center gap-2">
            <HealthDot
              state={
                models.isLoading
                  ? "loading"
                  : (models.data?.providers ?? []).some((p) => p.available)
                    ? "ok"
                    : "warn"
              }
            />
            <p className="text-sm font-medium">Model Router</p>
          </div>
          <p className="mt-1 text-xs text-muted-foreground">
            {providerHealth.filter((p) => p.available).length}/
            {providerHealth.length} providers reachable
          </p>
        </Card>
        <Card className="p-4">
          <div className="flex items-center gap-2">
            <HealthDot state="warn" />
            <p className="text-sm font-medium">Knowledge graph</p>
          </div>
          <p className="mt-1 text-xs text-muted-foreground">
            no health endpoint — checked per request
          </p>
        </Card>
        <Card className="p-4">
          <div className="flex items-center gap-2">
            <HealthDot state="ok" />
            <p className="text-sm font-medium">Policy</p>
          </div>
          <p className="mt-1 text-xs text-muted-foreground">
            v{models.data?.policy_version ?? "—"}
          </p>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Cpu className="size-4" /> Provider reachability
          </CardTitle>
        </CardHeader>
        <CardContent>
          {models.isLoading ? (
            <Skeleton className="h-24 w-full" />
          ) : (
            <ul className="divide-y divide-border text-sm">
              {providerHealth.map((p) => (
                <li key={p.name} className="flex items-center gap-3 py-2.5">
                  <HealthDot state={p.available ? "ok" : "warn"} />
                  <span className="font-mono text-xs">{p.name}</span>
                  <Badge variant="outline" className="ml-auto">
                    Class {p.hosting_class}
                  </Badge>
                  {p.leaves_perimeter && (
                    <Badge variant="warning">external</Badge>
                  )}
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <KeyRound className="size-4" /> API keys
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm text-muted-foreground">
            API keys are issued by a backend script, not an endpoint — there is
            no create-key API to call from here.
          </p>
          <CodeBlock
            code={`python scripts/create_api_key.py "My Org" "my-key-name" [role]`}
          />
          <p className="text-xs text-subtle-foreground">
            The raw key is printed once. Only its SHA-256 hash is stored. Send it
            as <code>Authorization: Bearer lai_…</code> on every request when{" "}
            <code>AUTH_REQUIRED=true</code>. Per-user login (the{" "}
            <code>sess_</code> token) is managed under the Users tab.
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Database className="size-4" /> Routing policy
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-muted-foreground">
          <p>
            The policy lives in <code>app/policies/routing.yaml</code>{" "}
            (version-controlled). Each task maps to an ordered candidate chain;
            a Class-C provider is appended only when external providers are
            enabled and the sensitivity tier is in{" "}
            <code>class_c_allowed_tiers</code>.
          </p>
          <div className="flex flex-wrap gap-2 pt-1">
            <Badge
              variant={
                models.data?.external_providers_enabled ? "info" : "success"
              }
            >
              external providers{" "}
              {models.data?.external_providers_enabled ? "enabled" : "off"}
            </Badge>
            {models.data?.strict_local_only && (
              <Badge variant="success">strict local only</Badge>
            )}
          </div>
          <p className="flex items-center gap-1.5 pt-1 text-xs">
            <Network className="size-3.5" /> Per-task Class-C kill switches are
            on the Models tab.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
