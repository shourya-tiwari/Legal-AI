"use client";

import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { Search, Sparkles, Filter } from "lucide-react";
import { analyzeNlp } from "@/lib/api";
import { qk } from "@/lib/query-keys";
import { useWorkspace } from "@/components/workspace/workspace-context";
import { ClauseCard } from "@/components/workspace/clause-card";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { ListSkeleton } from "@/components/shared/loaders";
import { ErrorState } from "@/components/ui/error-state";
import { EmptyState } from "@/components/ui/empty-state";
import { titleCase } from "@/lib/format";

export default function ClausesPage() {
  const { id, document } = useWorkspace();
  const [ai, setAi] = React.useState(false);
  const [q, setQ] = React.useState("");
  const [typeFilter, setTypeFilter] = React.useState<string | null>(null);

  const text = document.data?.full_text ?? "";
  const clauses = useQuery({
    queryKey: qk.nlp(id, ai),
    queryFn: () => analyzeNlp(text, ai),
    enabled: !!text,
  });

  const all = clauses.data?.clauses ?? [];
  const types = [...new Set(all.map((c) => c.clause_type))].sort();

  const filtered = all.filter((c) => {
    if (typeFilter && c.clause_type !== typeFilter) return false;
    if (q && !c.text.toLowerCase().includes(q.toLowerCase())) return false;
    return true;
  });

  const withDeontic = all.filter((c) => (c.deontic_tags ?? []).length > 0).length;
  const withAmbiguity = all.filter(
    (c) => (c.ambiguity_flags ?? []).length > 0,
  ).length;

  return (
    <div className="space-y-5">
      <Card>
        <CardContent className="flex flex-col gap-3 pt-5 sm:flex-row sm:items-center">
          <div className="relative flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-subtle-foreground" />
            <Input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Search clause text…"
              className="pl-9"
            />
          </div>
          <div className="flex items-center gap-2">
            <Switch id="ai" checked={ai} onCheckedChange={setAi} />
            <Label htmlFor="ai" className="flex items-center gap-1.5 text-sm">
              <Sparkles className="size-3.5" /> AI escalation
            </Label>
          </div>
        </CardContent>
      </Card>

      {clauses.isLoading || clauses.isFetching ? (
        <ListSkeleton rows={6} />
      ) : clauses.isError ? (
        <ErrorState error={clauses.error} onRetry={() => clauses.refetch()} />
      ) : all.length === 0 ? (
        <EmptyState
          icon={Filter}
          title="No clauses"
          description="The NLP pipeline returned nothing for this document."
        />
      ) : (
        <>
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <span className="text-subtle-foreground">
              {filtered.length}/{all.length} clauses · {withDeontic} with deontic
              tags · {withAmbiguity} flagged ambiguous
            </span>
          </div>

          <div className="flex flex-wrap gap-1.5">
            <button onClick={() => setTypeFilter(null)}>
              <Badge variant={typeFilter === null ? "primary" : "outline"}>
                All
              </Badge>
            </button>
            {types.map((t) => (
              <button key={t} onClick={() => setTypeFilter(t)}>
                <Badge variant={typeFilter === t ? "primary" : "outline"}>
                  {titleCase(t)} ·{" "}
                  {all.filter((c) => c.clause_type === t).length}
                </Badge>
              </button>
            ))}
          </div>

          <div className="space-y-3">
            {filtered.map((c) => (
              <ClauseCard key={c.id} clause={c} documentId={id} />
            ))}
            {filtered.length === 0 && (
              <EmptyState
                icon={Search}
                title="No matches"
                description="Try a different search or clause type."
                action={
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => {
                      setQ("");
                      setTypeFilter(null);
                    }}
                  >
                    Clear filters
                  </Button>
                }
              />
            )}
          </div>
        </>
      )}
    </div>
  );
}
