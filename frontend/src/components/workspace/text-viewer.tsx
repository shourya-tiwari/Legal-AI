"use client";

import * as React from "react";
import { Search } from "lucide-react";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";

/** Lightweight text viewer with in-document search + highlight. */
export function TextViewer({
  text,
  className,
  height = "h-[520px]",
}: {
  text: string;
  className?: string;
  height?: string;
}) {
  const [query, setQuery] = React.useState("");

  const segments = React.useMemo(() => {
    if (!query.trim()) return [{ t: text, match: false }];
    const parts: { t: string; match: boolean }[] = [];
    const re = new RegExp(
      `(${query.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")})`,
      "gi",
    );
    let last = 0;
    for (const m of text.matchAll(re)) {
      const idx = m.index ?? 0;
      if (idx > last) parts.push({ t: text.slice(last, idx), match: false });
      parts.push({ t: m[0], match: true });
      last = idx + m[0].length;
    }
    if (last < text.length) parts.push({ t: text.slice(last), match: false });
    return parts;
  }, [text, query]);

  const matchCount = query.trim()
    ? segments.filter((s) => s.match).length
    : 0;

  return (
    <div className={cn("flex flex-col gap-3", className)}>
      <div className="relative">
        <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-subtle-foreground" />
        <Input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search within the document…"
          className="pl-9"
        />
        {query.trim() && (
          <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-subtle-foreground">
            {matchCount} match{matchCount === 1 ? "" : "es"}
          </span>
        )}
      </div>
      <ScrollArea
        className={cn(
          "rounded-lg border border-border bg-background",
          height,
        )}
      >
        <pre className="whitespace-pre-wrap p-4 font-mono text-[13px] leading-relaxed text-muted-foreground">
          {segments.map((s, i) =>
            s.match ? (
              <mark
                key={i}
                className="rounded bg-warning/40 px-0.5 text-foreground"
              >
                {s.t}
              </mark>
            ) : (
              <React.Fragment key={i}>{s.t}</React.Fragment>
            ),
          )}
          {!text && "No text extracted from this document."}
        </pre>
      </ScrollArea>
    </div>
  );
}
