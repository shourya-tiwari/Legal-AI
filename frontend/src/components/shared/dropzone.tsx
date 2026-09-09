"use client";

import * as React from "react";
import { UploadCloud, FileText, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { bytes } from "@/lib/format";
import { Button } from "@/components/ui/button";

const ACCEPT = ".pdf,.docx,.txt,.png,.jpg,.jpeg";

export function Dropzone({
  onFile,
  disabled,
  file,
  onClear,
  className,
}: {
  onFile: (file: File) => void;
  disabled?: boolean;
  file?: File | null;
  onClear?: () => void;
  className?: string;
}) {
  const [dragOver, setDragOver] = React.useState(false);
  const inputRef = React.useRef<HTMLInputElement>(null);

  if (file) {
    return (
      <div
        className={cn(
          "flex items-center gap-3 rounded-xl border border-border bg-surface p-4",
          className,
        )}
      >
        <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-primary-muted text-primary">
          <FileText className="size-5" />
        </div>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium">{file.name}</p>
          <p className="text-xs text-muted-foreground">
            {bytes(file.size)} · {file.type || "unknown type"}
          </p>
        </div>
        {onClear && (
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={onClear}
            disabled={disabled}
            aria-label="Remove file"
          >
            <X />
          </Button>
        )}
      </div>
    );
  }

  return (
    <div
      role="button"
      tabIndex={0}
      aria-disabled={disabled}
      onClick={() => !disabled && inputRef.current?.click()}
      onKeyDown={(e) => {
        if ((e.key === "Enter" || e.key === " ") && !disabled) {
          e.preventDefault();
          inputRef.current?.click();
        }
      }}
      onDragOver={(e) => {
        e.preventDefault();
        if (!disabled) setDragOver(true);
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragOver(false);
        if (disabled) return;
        const f = e.dataTransfer.files?.[0];
        if (f) onFile(f);
      }}
      className={cn(
        "flex cursor-pointer flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed px-6 py-12 text-center transition-colors",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        dragOver
          ? "border-primary bg-primary-muted"
          : "border-border-strong hover:border-primary/50 hover:bg-muted/50",
        disabled && "pointer-events-none opacity-60",
        className,
      )}
    >
      <div className="flex size-12 items-center justify-center rounded-xl bg-muted text-muted-foreground">
        <UploadCloud className="size-6" />
      </div>
      <div className="space-y-1">
        <p className="text-sm font-medium">
          Drop a contract here, or <span className="text-primary">browse</span>
        </p>
        <p className="text-xs text-muted-foreground">
          PDF, DOCX, TXT, or a scanned image — up to a few MB
        </p>
      </div>
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPT}
        className="sr-only"
        disabled={disabled}
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) onFile(f);
          e.target.value = "";
        }}
      />
    </div>
  );
}
