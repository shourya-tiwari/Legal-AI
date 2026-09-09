"use client";

import * as React from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { FlaskConical, Play, CheckCircle2, XCircle, GitBranch, ListChecks } from "lucide-react";
import { toast } from "sonner";
import { getEvalRuns, runDeltaReport } from "@/lib/api";
import { qk } from "@/lib/query-keys";
import { PageHeader, PageBody } from "@/components/layout/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Stat } from "@/components/ui/stat";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ErrorState } from "@/components/ui/error-state";
import { EmptyState } from "@/components/ui/empty-state";
import { TableSkeleton } from "@/components/shared/loaders";
import { ScoreBar } from "@/components/shared/score-bar";
import { relativeTime, pct, ms } from "@/lib/format";

export default function EvaluationPage() {
  const runs = useQuery({ queryKey: qk.evalRuns, queryFn: getEvalRuns });
  const delta = useMutation({
    mutationFn: runDeltaReport,
    onError: (e) =>
      toast.error("Delta report failed", {
        description: String(e).includes("admin")
          ? "This action requires an admin role."
          : String(e),
      }),
  });

  const data = runs.data?.runs ?? [];
  const gated = data.filter((r) => r.passed != null);
  const passed = gated.filter((r) => r.passed).length;
  const tasks = [...new Set(data.map((r) => r.task))];

  return (
    <>
      <PageHeader
        title="Evaluation"
        description="The graded eval harness behind the routing policy. A task only cuts over to a self-hosted default when its candidate meets or beats the baseline."
        actions={
          <Button
            onClick={() => delta.mutate()}
            loading={delta.isPending}
            variant="secondary"
          >
            <Play /> Run delta report
          </Button>
        }
      />
      <PageBody className="space-y-6">
        <div className="grid gap-4 sm:grid-cols-3">
          <Stat label="Eval runs recorded" value={data.length} icon={FlaskConical} />
          <Stat
            label="Cutover gates passed"
            value={gated.length ? `${passed}/${gated.length}` : "—"}
            hint="candidate ≥ baseline × ratio"
            icon={GitBranch}
          />
          <Stat label="Tasks evaluated" value={tasks.length} icon={ListChecks} />
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Most recent run per task &amp; provider</CardTitle>
          </CardHeader>
          <CardContent>
            {runs.isLoading ? (
              <TableSkeleton />
            ) : runs.isError ? (
              <ErrorState error={runs.error} onRetry={() => runs.refetch()} />
            ) : data.length === 0 ? (
              <EmptyState
                icon={FlaskConical}
                title="No eval runs yet"
                description="The eval_runs table is empty — run the cutover gate or a graded task from the backend."
              />
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Task</TableHead>
                    <TableHead>Provider</TableHead>
                    <TableHead>Metric</TableHead>
                    <TableHead className="w-48">Score vs baseline</TableHead>
                    <TableHead>Gate</TableHead>
                    <TableHead>When</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.map((r, i) => (
                    <TableRow key={i}>
                      <TableCell className="font-mono text-xs">{r.task}</TableCell>
                      <TableCell className="text-xs text-muted-foreground">
                        {r.provider}
                        <span className="block text-[10px] text-subtle-foreground">
                          {r.model}
                        </span>
                      </TableCell>
                      <TableCell className="text-xs">
                        {r.metric}
                        <span className="block text-[10px] text-subtle-foreground">
                          n={r.n_examples}
                        </span>
                      </TableCell>
                      <TableCell>
                        <ScoreBar
                          score={r.score}
                          baseline={r.baseline_score}
                          passed={r.passed}
                        />
                      </TableCell>
                      <TableCell>
                        {r.passed == null ? (
                          <Badge variant="default">—</Badge>
                        ) : r.passed ? (
                          <Badge variant="success">
                            <CheckCircle2 /> pass
                          </Badge>
                        ) : (
                          <Badge variant="danger">
                            <XCircle /> fail
                          </Badge>
                        )}
                      </TableCell>
                      <TableCell className="text-xs text-subtle-foreground">
                        {relativeTime(r.created_at)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>

        {(delta.data || delta.isPending) && (
          <Card>
            <CardHeader>
              <CardTitle>Self-hosted vs external — delta report</CardTitle>
            </CardHeader>
            <CardContent>
              {delta.isPending ? (
                <p className="text-sm text-muted-foreground">
                  Making real generation calls against local-llm and gemini for
                  every fixture task…
                </p>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Task</TableHead>
                      <TableHead>Local</TableHead>
                      <TableHead>External</TableHead>
                      <TableHead>Agreement F1</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {(delta.data?.rows ?? []).map((row, i) => (
                      <TableRow key={i}>
                        <TableCell className="font-mono text-xs">
                          {row.task}
                        </TableCell>
                        <TableCell className="text-xs">
                          {row.local_error ? (
                            <span className="text-danger">
                              {row.local_error}
                            </span>
                          ) : (
                            `${ms(row.local_ms)} · ${row.local_len} chars`
                          )}
                        </TableCell>
                        <TableCell className="text-xs">
                          {row.external_error ? (
                            <span className="text-danger">
                              {row.external_error}
                            </span>
                          ) : (
                            `${ms(row.external_ms)} · ${row.external_len} chars`
                          )}
                        </TableCell>
                        <TableCell>
                          <Badge
                            variant={
                              row.agreement_f1 > 0.7
                                ? "success"
                                : row.agreement_f1 > 0.4
                                  ? "warning"
                                  : "danger"
                            }
                          >
                            {pct(row.agreement_f1, 0)}
                          </Badge>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        )}
      </PageBody>
    </>
  );
}
