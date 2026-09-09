"use client";

import * as React from "react";
import { useMutation } from "@tanstack/react-query";
import { Wand2 } from "lucide-react";
import { rewriteDocument } from "@/lib/api";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { ScrollArea } from "@/components/ui/scroll-area";
import { ErrorState } from "@/components/ui/error-state";
import { CopyButton } from "@/components/shared/copy-button";

export function RewriteDialog({
  documentId,
  blockId,
  original,
  trigger,
}: {
  documentId: number;
  blockId?: string | number | null;
  original?: string;
  trigger: React.ReactNode;
}) {
  const [open, setOpen] = React.useState(false);
  const rewrite = useMutation({
    mutationFn: () => rewriteDocument(documentId, blockId),
  });

  React.useEffect(() => {
    if (open && !rewrite.data && !rewrite.isPending) rewrite.mutate();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>{trigger}</DialogTrigger>
      <DialogContent className="max-w-3xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Wand2 className="size-4 text-primary" />
            Plain-English rewrite
            {blockId != null && (
              <span className="text-xs font-normal text-muted-foreground">
                clause {blockId}
              </span>
            )}
          </DialogTitle>
          <DialogDescription>
            The legalese, translated. Facts are retained; jargon is removed.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4 sm:grid-cols-2">
          {original && (
            <div className="space-y-1.5">
              <p className="text-xs font-medium text-subtle-foreground">
                Original
              </p>
              <ScrollArea className="h-64 rounded-lg border border-border bg-background">
                <p className="p-3 text-sm text-muted-foreground">{original}</p>
              </ScrollArea>
            </div>
          )}
          <div className={original ? "space-y-1.5" : "sm:col-span-2 space-y-1.5"}>
            <div className="flex items-center justify-between">
              <p className="text-xs font-medium text-subtle-foreground">
                Plain English
              </p>
              {rewrite.data && (
                <CopyButton
                  value={rewrite.data.rewritten_text}
                  size="sm"
                  label="Copy"
                />
              )}
            </div>
            {rewrite.isPending ? (
              <div className="space-y-2 rounded-lg border border-border p-3">
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-11/12" />
                <Skeleton className="h-4 w-3/4" />
              </div>
            ) : rewrite.isError ? (
              <ErrorState
                error={rewrite.error}
                onRetry={() => rewrite.mutate()}
              />
            ) : (
              <ScrollArea className="h-64 rounded-lg border border-border bg-background">
                <p className="whitespace-pre-wrap p-3 text-sm">
                  {rewrite.data?.rewritten_text}
                </p>
              </ScrollArea>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
