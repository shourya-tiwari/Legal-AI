import * as React from "react";
import { cn } from "@/lib/utils";

/**
 * A window-chrome wrapper for the "screenshots" section. The content inside is
 * a real, simplified rendering built from the design system — not a bitmap —
 * so it always matches the current theme and never goes stale.
 */
export function BrowserFrame({
  url = "legalai.app",
  children,
  className,
}: {
  url?: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "overflow-hidden rounded-xl border border-border bg-surface shadow-lg",
        className,
      )}
    >
      <div className="flex items-center gap-2 border-b border-border bg-elevated px-3 py-2">
        <div className="flex gap-1.5">
          <span className="size-2.5 rounded-full bg-border-strong" />
          <span className="size-2.5 rounded-full bg-border-strong" />
          <span className="size-2.5 rounded-full bg-border-strong" />
        </div>
        <div className="mx-auto flex items-center gap-1.5 rounded-md bg-surface px-3 py-1 text-[11px] text-subtle-foreground">
          {url}
        </div>
      </div>
      <div className="p-4">{children}</div>
    </div>
  );
}
