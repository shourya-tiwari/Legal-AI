"use client";

import * as React from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Flag, Webhook, Save } from "lucide-react";
import { getOrgSettings, updateOrgSettings } from "@/lib/api";
import { qk } from "@/lib/query-keys";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/ui/error-state";
import { titleCase } from "@/lib/format";

const KNOWN_FLAGS: { key: string; label: string; blurb: string }[] = [
  {
    key: "api_v2_enabled",
    label: "API v2",
    blurb: "Gates every /api/v2/* route. Default on — turning it off breaks the document-first API.",
  },
];

export default function AdminFlagsPage() {
  const qc = useQueryClient();
  const q = useQuery({
    queryKey: qk.orgSettings,
    queryFn: getOrgSettings,
    retry: false,
  });

  const webhookRef = React.useRef<HTMLInputElement>(null);
  const flags = (q.data?.feature_flags ?? {}) as Record<string, boolean>;
  const allFlagKeys = [
    ...new Set([...KNOWN_FLAGS.map((f) => f.key), ...Object.keys(flags)]),
  ];

  const save = useMutation({
    mutationFn: (patch: Parameters<typeof updateOrgSettings>[0]) =>
      updateOrgSettings(patch),
    onSuccess: () => {
      toast.success("Saved");
      qc.invalidateQueries({ queryKey: qk.orgSettings });
    },
    onError: (e) =>
      toast.error("Save failed", {
        description: String(e).includes("admin")
          ? "Requires an admin role."
          : String(e),
      }),
  });

  if (q.isLoading) return <Skeleton className="h-64 w-full" />;
  if (q.isError)
    return (
      <ErrorState
        error={q.error}
        title="Could not load org settings"
        onRetry={() => q.refetch()}
      />
    );

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Flag className="size-4" /> Feature flags
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="mb-4 text-sm text-muted-foreground">
            A flag missing from the org&rsquo;s dict falls back to a hardcoded
            default, so a new flag never breaks a pre-existing org.
          </p>
          <ul className="divide-y divide-border">
            {allFlagKeys.map((key) => {
              const meta = KNOWN_FLAGS.find((f) => f.key === key);
              const value = flags[key] ?? true;
              return (
                <li
                  key={key}
                  className="flex items-center justify-between gap-4 py-3"
                >
                  <div>
                    <p className="text-sm font-medium">
                      {meta?.label ?? titleCase(key)}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {meta?.blurb ?? `Custom flag: ${key}`}
                    </p>
                  </div>
                  <Switch
                    checked={value}
                    onCheckedChange={(v) =>
                      save.mutate({ feature_flags: { [key]: v } })
                    }
                    aria-label={`Toggle ${key}`}
                  />
                </li>
              );
            })}
          </ul>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Webhook className="size-4" /> Completion webhook
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm text-muted-foreground">
            Fires a fail-soft <code>POST</code> after an agent analysis
            completes (<code>event: analysis.completed</code>). Sent via
            background task — a slow or dead endpoint never delays the response.
          </p>
          <div className="space-y-1.5">
            <Label htmlFor="wh">Webhook URL</Label>
            <div className="flex gap-2">
              <Input
                id="wh"
                type="url"
                ref={webhookRef}
                key={q.data?.webhook_url ?? "none"}
                defaultValue={q.data?.webhook_url ?? ""}
                placeholder="https://example.com/hooks/legalai"
              />
              <Button
                onClick={() =>
                  save.mutate({
                    webhook_url: webhookRef.current?.value.trim() || "",
                  })
                }
                loading={save.isPending}
              >
                <Save /> Save
              </Button>
            </div>
            <p className="text-xs text-subtle-foreground">
              Leave empty and save to clear it.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
