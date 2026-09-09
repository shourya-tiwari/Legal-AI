"use client";

import * as React from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { ClipboardCheck, FileWarning } from "lucide-react";
import {
  getReviewQueue,
  resolveReviewItem,
  type ReviewQueueItem,
} from "@/lib/api";
import { qk } from "@/lib/query-keys";
import { PageHeader, PageBody } from "@/components/layout/page-header";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { ListSkeleton } from "@/components/shared/loaders";
import { FaithfulnessBadge } from "@/components/shared/faithfulness-badge";
import { relativeTime } from "@/lib/format";

export default function ReviewPage() {
  const [includeResolved, setIncludeResolved] = React.useState(false);
  const qc = useQueryClient();

  const q = useQuery({
    queryKey: qk.reviewQueue(includeResolved),
    queryFn: () => getReviewQueue(includeResolved),
  });

  const items = q.data?.items ?? [];

  return (
    <>
      <PageHeader
        title="Human review queue"
        description="Every agent analysis the Verifier flagged needs_human_review — a knowledge-graph conflict, an invalid citation, or a faithfulness check that failed."
        actions={
          <div className="flex items-center gap-2">
            <Switch
              id="show-resolved"
              checked={includeResolved}
              onCheckedChange={setIncludeResolved}
            />
            <Label htmlFor="show-resolved" className="text-sm">
              Show resolved
            </Label>
          </div>
        }
      />
      <PageBody className="max-w-4xl space-y-4">
        {q.isLoading ? (
          <ListSkeleton />
        ) : q.isError ? (
          <ErrorState error={q.error} onRetry={() => q.refetch()} />
        ) : items.length === 0 ? (
          <EmptyState
            icon={ClipboardCheck}
            title={
              includeResolved
                ? "No analyses have ever been flagged"
                : "Nothing needs review"
            }
            description="When an agent analysis fails verification, it lands here for a human to sign off."
          />
        ) : (
          items.map((item) => (
            <ReviewCard
              key={item.id}
              item={item}
              onResolved={() =>
                qc.invalidateQueries({ queryKey: ["review-queue"] })
              }
            />
          ))
        )}
      </PageBody>
    </>
  );
}

function ReviewCard({
  item,
  onResolved,
}: {
  item: ReviewQueueItem;
  onResolved: () => void;
}) {
  const [note, setNote] = React.useState("");
  const resolve = useMutation({
    mutationFn: () => resolveReviewItem(item.id, note.trim() || undefined),
    onSuccess: () => {
      toast.success("Marked reviewed");
      onResolved();
    },
    onError: (e) => toast.error("Could not resolve", { description: String(e) }),
  });

  return (
    <Card>
      <CardContent className="space-y-3 pt-5">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <FileWarning className="size-4 text-warning" />
            <Link
              href={`/documents/${item.document_id}`}
              className="text-sm font-semibold hover:text-primary"
            >
              {item.document_filename}
            </Link>
            <span className="text-xs text-subtle-foreground">
              {relativeTime(item.created_at)} · {item.analysis_mode}
            </span>
          </div>
          {item.reviewed ? (
            <Badge variant="success">
              reviewed {item.reviewed_at ? relativeTime(item.reviewed_at) : ""}
            </Badge>
          ) : (
            <Badge variant="warning">needs review</Badge>
          )}
        </div>

        <p className="text-sm text-muted-foreground">{item.summary}</p>

        <div className="flex flex-wrap gap-1.5">
          <FaithfulnessBadge
            ok={item.faithfulness_ok}
            method={item.faithfulness_method}
            unsupportedCount={(item.unsupported_claims ?? []).length}
          />
          {(item.invalid_citation_numbers ?? []).length > 0 && (
            <Badge variant="danger">
              invalid citations: {(item.invalid_citation_numbers ?? []).join(", ")}
            </Badge>
          )}
          {(item.plan ?? []).length > 0 && (
            <Badge variant="outline">plan: {(item.plan ?? []).join(" → ")}</Badge>
          )}
        </div>

        {(item.unsupported_claims ?? []).length > 0 && (
          <ul className="space-y-1 rounded-lg border border-warning/30 bg-warning/10 p-3 text-xs text-muted-foreground">
            {(item.unsupported_claims ?? []).map((c, i) => (
              <li key={i}>• {c}</li>
            ))}
          </ul>
        )}

        {item.reviewed
          ? item.reviewer_note && (
              <p className="text-xs italic text-subtle-foreground">
                Note: {item.reviewer_note}
              </p>
            )
          : !item.reviewed && (
              <div className="flex flex-col gap-2 sm:flex-row">
                <Input
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  placeholder="Optional note — what you checked…"
                  className="flex-1"
                />
                <Button
                  onClick={() => resolve.mutate()}
                  loading={resolve.isPending}
                  variant="secondary"
                >
                  Mark reviewed
                </Button>
              </div>
            )}
      </CardContent>
    </Card>
  );
}
