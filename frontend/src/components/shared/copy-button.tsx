"use client";

import * as React from "react";
import { Check, Copy } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export function CopyButton({
  value,
  label,
  className,
  size = "icon-sm",
  variant = "ghost",
}: {
  value: string;
  label?: string;
  className?: string;
  size?: "icon-sm" | "sm";
  variant?: "ghost" | "secondary" | "outline";
}) {
  const [copied, setCopied] = React.useState(false);

  return (
    <Button
      type="button"
      variant={variant}
      size={size === "sm" ? "sm" : "icon-sm"}
      className={className}
      aria-label={label ?? "Copy"}
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(value);
          setCopied(true);
          setTimeout(() => setCopied(false), 1600);
        } catch {
          /* clipboard unavailable */
        }
      }}
    >
      {copied ? (
        <Check className={cn("text-success", size === "sm" && "size-3.5")} />
      ) : (
        <Copy className={cn(size === "sm" && "size-3.5")} />
      )}
      {size === "sm" && (label ?? (copied ? "Copied" : "Copy"))}
    </Button>
  );
}
