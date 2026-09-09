"use client";

import { Sparkles } from "lucide-react";
import { EmptyState } from "@/components/ui/empty-state";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { ErrorState } from "@/components/ui/error-state";

export function RunAnalysisCta({
  title,
  description,
  isPending,
  isError,
  error,
  onRun,
}: {
  title: string;
  description: string;
  isPending: boolean;
  isError: boolean;
  error?: unknown;
  onRun: () => void;
}) {
  if (isPending) {
    return (
      <div className="flex flex-col items-center gap-3 rounded-xl border border-dashed border-border py-16 text-center">
        <Spinner className="size-6" />
        <p className="text-sm text-muted-foreground">
          Planning &amp; running the agent pipeline…
        </p>
      </div>
    );
  }
  if (isError) {
    return <ErrorState error={error} title="Analysis failed" onRetry={onRun} />;
  }
  return (
    <EmptyState
      icon={Sparkles}
      title={title}
      description={description}
      action={
        <Button onClick={onRun}>
          <Sparkles /> Run analysis
        </Button>
      }
    />
  );
}
