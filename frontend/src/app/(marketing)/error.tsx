"use client";

import { RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function MarketingError({ reset }: { reset: () => void }) {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-4 px-4 text-center">
      <h1 className="text-xl font-semibold tracking-tight">
        This page hit an error
      </h1>
      <p className="max-w-md text-sm text-muted-foreground">
        Try again, or head back to the homepage.
      </p>
      <Button onClick={reset} variant="secondary">
        <RefreshCw /> Try again
      </Button>
    </div>
  );
}
