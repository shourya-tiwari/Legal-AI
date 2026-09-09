"use client";

import { AlertTriangle, RefreshCw } from "lucide-react";
import { ApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export function ErrorState({
  error,
  onRetry,
  title = "Something went wrong",
  className,
}: {
  error?: unknown;
  onRetry?: () => void;
  title?: string;
  className?: string;
}) {
  const message =
    error instanceof ApiError
      ? error.status === 404
        ? "Not found."
        : error.status === 503
          ? "The service is temporarily unavailable. Try again shortly."
          : error.message || `Request failed (${error.status}).`
      : error instanceof Error
        ? error.message
        : "An unexpected error occurred.";

  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-3 rounded-xl border border-danger/30 bg-danger/[0.06] px-6 py-12 text-center",
        className,
      )}
    >
      <div className="flex size-11 items-center justify-center rounded-xl bg-danger/15 text-danger">
        <AlertTriangle className="size-5" />
      </div>
      <div className="space-y-1">
        <p className="text-sm font-medium text-foreground">{title}</p>
        <p className="mx-auto max-w-md text-sm text-muted-foreground">{message}</p>
      </div>
      {onRetry && (
        <Button variant="secondary" size="sm" onClick={onRetry} className="mt-1">
          <RefreshCw />
          Retry
        </Button>
      )}
    </div>
  );
}
