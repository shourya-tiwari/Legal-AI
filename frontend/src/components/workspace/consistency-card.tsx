"use client";

import { useMutation } from "@tanstack/react-query";
import { GitCompareArrows, AlertTriangle, ScanSearch } from "lucide-react";
import { checkConsistency } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Spinner } from "@/components/ui/spinner";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { pct, MODALITY_META } from "@/lib/format";

export function ConsistencyCard({ documentId }: { documentId: number }) {
  const check = useMutation({
    mutationFn: () => checkConsistency(documentId),
  });

  const findings = check.data?.findings ?? [];
  const conflicts = findings.filter((f) => f.is_conflict);

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between">
        <CardTitle className="flex items-center gap-2">
          <GitCompareArrows className="size-4" /> Cross-document consistency
        </CardTitle>
        {check.data && (
          <span className="text-xs text-subtle-foreground">
            {check.data.other_documents_checked} other doc(s) checked
          </span>
        )}
      </CardHeader>
      <CardContent className="space-y-3">
        {!check.data && !check.isPending && (
          <p className="text-sm text-muted-foreground">
            Embeds every deontic-tagged clause in this document and compares it
            against your other documents — catching contradictions that use
            different wording and different defined terms, which an exact-term
            match can&rsquo;t see.
          </p>
        )}
        {check.isPending && (
          <span className="flex items-center gap-2 text-sm text-muted-foreground">
            <Spinner /> Embedding &amp; comparing clauses…
          </span>
        )}
        {check.isError && (
          <ErrorState error={check.error} title="Consistency check failed" />
        )}
        {check.data && findings.length === 0 && (
          <EmptyState
            icon={ScanSearch}
            title="No overlapping clauses"
            description="Nothing in your other documents is semantically close enough to compare — or you only have this one document."
          />
        )}
        {findings.length > 0 && (
          <>
            {conflicts.length > 0 && (
              <div className="flex items-center gap-2 rounded-lg border border-danger/30 bg-danger/10 p-2.5 text-sm text-danger">
                <AlertTriangle className="size-4" />
                {conflicts.length} active modality conflict
                {conflicts.length === 1 ? "" : "s"}
              </div>
            )}
            <ul className="space-y-3">
              {findings.slice(0, 6).map((f, i) => (
                <li
                  key={i}
                  className={`rounded-lg border p-3 text-sm ${
                    f.is_conflict
                      ? "border-danger/30 bg-danger/[0.04]"
                      : "border-border bg-surface"
                  }`}
                >
                  <div className="mb-1.5 flex flex-wrap items-center gap-1.5">
                    <Badge variant={f.is_conflict ? "danger" : "outline"}>
                      {pct(f.similarity)} similar
                    </Badge>
                    <Badge
                      variant="outline"
                      className={MODALITY_META[f.modality]?.className}
                    >
                      this: {f.modality}
                    </Badge>
                    <Badge
                      variant="outline"
                      className={MODALITY_META[f.other_modality]?.className}
                    >
                      {f.other_document_filename}: {f.other_modality}
                    </Badge>
                  </div>
                  <p className="text-xs text-muted-foreground">{f.clause_text}</p>
                  <p className="mt-1 text-xs text-subtle-foreground">
                    ↔ {f.other_clause_text}
                  </p>
                </li>
              ))}
            </ul>
          </>
        )}
        <Button
          variant={check.data ? "secondary" : "primary"}
          size="sm"
          onClick={() => check.mutate()}
          loading={check.isPending}
        >
          <ScanSearch />
          {check.data ? "Re-check" : "Check consistency"}
        </Button>
      </CardContent>
    </Card>
  );
}
