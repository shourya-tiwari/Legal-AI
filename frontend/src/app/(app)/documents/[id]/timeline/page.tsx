"use client";

import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { CalendarClock, CalendarCheck, CalendarX } from "lucide-react";
import { mapDocument, simulateTimeline } from "@/lib/api";
import { qk } from "@/lib/query-keys";
import { useWorkspace } from "@/components/workspace/workspace-context";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/ui/error-state";
import { EmptyState } from "@/components/ui/empty-state";
import { shortDate, titleCase, MODALITY_META } from "@/lib/format";
import { cn } from "@/lib/utils";

const STATUS_META: Record<
  string,
  { label: string; className: string; dot: string }
> = {
  past: { label: "Past", className: "text-subtle-foreground", dot: "bg-border-strong" },
  upcoming: { label: "Upcoming", className: "text-warning", dot: "bg-warning" },
  future: { label: "Future", className: "text-info", dot: "bg-info" },
};

export default function TimelinePage() {
  const { id } = useWorkspace();
  const [refDate, setRefDate] = React.useState("");
  const [window, setWindow] = React.useState(30);

  const map = useQuery({ queryKey: qk.map(id), queryFn: () => mapDocument(id) });
  const sim = useQuery({
    queryKey: qk.simulate(id, refDate || "today", window),
    queryFn: () =>
      simulateTimeline(id, {
        reference_date: refDate || undefined,
        warning_window_days: window,
      }),
  });

  const events = sim.data?.events ?? [];
  const structure = map.data?.structure ?? [];
  const descriptive = map.data?.timeline ?? [];

  const counts = {
    past: events.filter((e) => e.status === "past").length,
    upcoming: events.filter((e) => e.status === "upcoming").length,
    future: events.filter((e) => e.status === "future").length,
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardContent className="flex flex-col gap-4 pt-5 sm:flex-row sm:items-end">
          <div className="space-y-1.5">
            <Label htmlFor="ref">Simulate from</Label>
            <Input
              id="ref"
              type="date"
              value={refDate}
              onChange={(e) => setRefDate(e.target.value)}
              className="w-44"
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="win">Warning window (days)</Label>
            <Input
              id="win"
              type="number"
              min={1}
              max={365}
              value={window}
              onChange={(e) => setWindow(Number(e.target.value) || 30)}
              className="w-32"
            />
          </div>
          <div className="flex flex-1 flex-wrap gap-2 sm:justify-end">
            <Badge variant="default">
              <CalendarX /> {counts.past} past
            </Badge>
            <Badge variant="warning">
              <CalendarClock /> {counts.upcoming} upcoming
            </Badge>
            <Badge variant="info">
              <CalendarCheck /> {counts.future} future
            </Badge>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
        <Card>
          <CardHeader>
            <CardTitle>Dated obligations</CardTitle>
          </CardHeader>
          <CardContent>
            {sim.isLoading ? (
              <div className="space-y-2">
                <Skeleton className="h-12 w-full" />
                <Skeleton className="h-12 w-full" />
              </div>
            ) : sim.isError ? (
              <ErrorState error={sim.error} onRetry={() => sim.refetch()} />
            ) : events.length === 0 ? (
              <EmptyState
                icon={CalendarClock}
                title="No resolved dates"
                description="Only clauses with an absolute date become events — bare durations like “30 days” are left honestly unresolved."
              />
            ) : (
              <ol className="relative space-y-4 border-l border-border pl-5">
                {events.map((e, i) => {
                  const meta = STATUS_META[e.status] ?? STATUS_META.future;
                  const mod = MODALITY_META[e.modality];
                  return (
                    <li key={i} className="relative">
                      <span
                        className={cn(
                          "absolute -left-[23px] top-1.5 size-2.5 rounded-full ring-4 ring-background",
                          meta.dot,
                        )}
                      />
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-sm font-medium">
                          {shortDate(e.date)}
                        </span>
                        <span
                          className={cn("text-xs font-medium", meta.className)}
                        >
                          {meta.label}
                        </span>
                        {mod && e.modality !== "none" && (
                          <Badge variant="outline" className={mod.className}>
                            {mod.label}
                          </Badge>
                        )}
                      </div>
                      <p className="mt-0.5 text-xs text-subtle-foreground">
                        {e.date_text} · clause #{e.clause_id} ·{" "}
                        {titleCase(e.clause_type)}
                      </p>
                      <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">
                        {e.clause_text}
                      </p>
                    </li>
                  );
                })}
              </ol>
            )}
          </CardContent>
        </Card>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Descriptive timeline</CardTitle>
            </CardHeader>
            <CardContent>
              {map.isLoading ? (
                <Skeleton className="h-24 w-full" />
              ) : descriptive.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No time-based events extracted.
                </p>
              ) : (
                <ul className="space-y-2">
                  {descriptive.map((t, i) => (
                    <li key={i} className="text-sm">
                      <span className="font-medium">{t.date_description}</span>
                      <span className="text-muted-foreground"> — {t.event}</span>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Structure</CardTitle>
            </CardHeader>
            <CardContent>
              {map.isLoading ? (
                <Skeleton className="h-24 w-full" />
              ) : structure.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No section structure detected.
                </p>
              ) : (
                <ul className="space-y-1.5 text-sm">
                  {structure.map((s, i) => (
                    <li key={i}>
                      <p className="font-medium">{s.title}</p>
                      {s.content_summary && (
                        <p className="text-xs text-muted-foreground">
                          {s.content_summary}
                        </p>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
