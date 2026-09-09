"use client";

import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { History } from "lucide-react";
import { getKgVersions } from "@/lib/api";
import { qk } from "@/lib/query-keys";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { DropdownMenuItem } from "@/components/ui/dropdown-menu";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";

export function VersionHistoryDialog({ documentId }: { documentId: number }) {
  const [open, setOpen] = React.useState(false);
  const q = useQuery({
    queryKey: qk.kgVersions(documentId),
    queryFn: () => getKgVersions(documentId),
    enabled: open,
  });

  const versions = (q.data?.versions ?? []) as Record<string, unknown>[];

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DropdownMenuItem
        onSelect={(e) => {
          e.preventDefault();
          setOpen(true);
        }}
      >
        <History /> Version history
      </DropdownMenuItem>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Version history</DialogTitle>
          <DialogDescription>
            The SUPERSEDES chain from the knowledge graph (bitemporal
            versioning). Requires the document to have been ingested.
          </DialogDescription>
        </DialogHeader>
        {q.isLoading ? (
          <div className="space-y-2">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
          </div>
        ) : versions.length === 0 ? (
          <EmptyState
            icon={History}
            title="No version chain"
            description="This document hasn't been superseded, or the knowledge graph is offline."
          />
        ) : (
          <ol className="space-y-2">
            {versions.map((v, i) => (
              <li
                key={i}
                className="flex items-center justify-between gap-3 rounded-lg border border-border bg-surface p-3 text-sm"
              >
                <span className="font-mono text-xs">
                  doc {String(v.document_id ?? v.id ?? "?")}
                </span>
                <span className="text-muted-foreground">
                  {String(v.valid_from ?? v.created_at ?? "")}
                </span>
                {i === 0 && <Badge variant="success">current</Badge>}
              </li>
            ))}
          </ol>
        )}
      </DialogContent>
    </Dialog>
  );
}
