"use client";

import { useQuery } from "@tanstack/react-query";
import { ExternalLink, Fingerprint } from "lucide-react";
import { getEgressLog } from "@/lib/api";
import { qk } from "@/lib/query-keys";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tooltip } from "@/components/ui/tooltip";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { TableSkeleton } from "@/components/shared/loaders";
import { dateTime } from "@/lib/format";

export default function AdminEgressPage() {
  const q = useQuery({
    queryKey: qk.egress(200),
    queryFn: () => getEgressLog(200),
  });

  const entries = q.data?.entries ?? [];

  return (
    <div className="space-y-5">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ExternalLink className="size-4" /> Class-C egress audit trail
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">
            One row per successful Class-C dispatch: the task, provider, model,
            policy version, a SHA-256 of the exact text sent (never the payload
            itself), and the PII redaction gate&rsquo;s category counts. Written
            by <code>model_router/telemetry.py::record_egress</code>. Not
            org-scoped yet — a documented backend gap.
          </p>

          {q.isLoading ? (
            <TableSkeleton rows={8} />
          ) : q.isError ? (
            <ErrorState error={q.error} onRetry={() => q.refetch()} />
          ) : entries.length === 0 ? (
            <EmptyState
              icon={ExternalLink}
              title="Nothing has left the perimeter"
              description="No request has been dispatched to an external (Class C) provider — either external providers are off, or every document has been self-hosted-only."
            />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>When</TableHead>
                  <TableHead>Task</TableHead>
                  <TableHead>Provider / model</TableHead>
                  <TableHead>Tier</TableHead>
                  <TableHead>Redacted</TableHead>
                  <TableHead>Payload hash</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {entries.map((e) => {
                  const redacted = Object.entries(
                    (e.redacted_categories ?? {}) as Record<string, number>,
                  ).filter(([, v]) => v > 0);
                  return (
                    <TableRow key={e.id}>
                      <TableCell className="whitespace-nowrap text-xs text-muted-foreground">
                        {dateTime(e.created_at)}
                      </TableCell>
                      <TableCell className="font-mono text-xs">{e.task}</TableCell>
                      <TableCell className="text-xs">
                        {e.provider}
                        <span className="block text-[10px] text-subtle-foreground">
                          {e.model} · policy v{e.policy_version}
                        </span>
                      </TableCell>
                      <TableCell>
                        {e.sensitivity && (
                          <Badge variant="outline" className="capitalize">
                            {e.sensitivity}
                          </Badge>
                        )}
                      </TableCell>
                      <TableCell>
                        {redacted.length === 0 ? (
                          <span className="text-xs text-subtle-foreground">
                            none
                          </span>
                        ) : (
                          <div className="flex flex-wrap gap-1">
                            {redacted.map(([cat, n]) => (
                              <Badge key={cat} variant="warning">
                                {cat} ×{n}
                              </Badge>
                            ))}
                          </div>
                        )}
                      </TableCell>
                      <TableCell>
                        {e.payload_sha256 && (
                          <Tooltip content={e.payload_sha256}>
                            <span className="flex items-center gap-1 font-mono text-[10px] text-subtle-foreground">
                              <Fingerprint className="size-3" />
                              {e.payload_sha256.slice(0, 10)}…
                            </span>
                          </Tooltip>
                        )}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
