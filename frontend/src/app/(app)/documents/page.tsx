"use client";

import * as React from "react";
import Link from "next/link";
import {
  Upload,
  Search,
  LayoutGrid,
  List,
  FileText,
  Trash2,
  Tag as TagIcon,
} from "lucide-react";
import { toast } from "sonner";
import { useDocuments, allTags } from "@/lib/stores/documents";
import { useUI } from "@/lib/stores/ui";
import { PageHeader, PageBody } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { SensitivityBadge } from "@/components/shared/sensitivity-badge";
import { relativeTime } from "@/lib/format";
import { cn } from "@/lib/utils";

export default function DocumentsPage() {
  const docs = useDocuments((s) => s.docs);
  const remove = useDocuments((s) => s.remove);
  const view = useUI((s) => s.docsView);
  const setView = useUI((s) => s.setDocsView);

  const [q, setQ] = React.useState("");
  const [tier, setTier] = React.useState<string>("all");
  const [tag, setTag] = React.useState<string>("all");

  const tags = allTags(docs);

  const filtered = docs.filter((d) => {
    if (q && !d.filename.toLowerCase().includes(q.toLowerCase())) return false;
    if (tier !== "all" && d.sensitivityTier !== tier) return false;
    if (tag !== "all" && !d.tags.includes(tag)) return false;
    return true;
  });

  return (
    <>
      <PageHeader
        title="Documents"
        description="Contracts you've uploaded from this browser. Each opens into a full analysis workspace."
        actions={
          <Button asChild>
            <Link href="/documents/upload">
              <Upload /> Upload
            </Link>
          </Button>
        }
      />
      <PageBody className="space-y-5">
        {docs.length === 0 ? (
          <EmptyState
            icon={FileText}
            title="Your library is empty"
            description="Upload a contract to get started. The backend has no server-side document list, so your library is scoped to this browser."
            action={
              <Button asChild>
                <Link href="/documents/upload">
                  <Upload /> Upload a document
                </Link>
              </Button>
            }
          />
        ) : (
          <>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
              <div className="relative flex-1">
                <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-subtle-foreground" />
                <Input
                  value={q}
                  onChange={(e) => setQ(e.target.value)}
                  placeholder="Search by filename…"
                  className="pl-9"
                />
              </div>
              <Select value={tier} onValueChange={setTier}>
                <SelectTrigger className="w-full sm:w-40">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All tiers</SelectItem>
                  <SelectItem value="public">Public</SelectItem>
                  <SelectItem value="internal">Internal</SelectItem>
                  <SelectItem value="confidential">Confidential</SelectItem>
                  <SelectItem value="privileged">Privileged</SelectItem>
                </SelectContent>
              </Select>
              {tags.length > 0 && (
                <Select value={tag} onValueChange={setTag}>
                  <SelectTrigger className="w-full sm:w-40">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All tags</SelectItem>
                    {tags.map((t) => (
                      <SelectItem key={t} value={t}>
                        {t}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
              <div className="flex rounded-lg border border-border p-0.5">
                <button
                  onClick={() => setView("grid")}
                  className={cn(
                    "rounded-md p-1.5 transition-colors",
                    view === "grid"
                      ? "bg-muted text-foreground"
                      : "text-subtle-foreground hover:text-foreground",
                  )}
                  aria-label="Grid view"
                  aria-pressed={view === "grid"}
                >
                  <LayoutGrid className="size-4" />
                </button>
                <button
                  onClick={() => setView("list")}
                  className={cn(
                    "rounded-md p-1.5 transition-colors",
                    view === "list"
                      ? "bg-muted text-foreground"
                      : "text-subtle-foreground hover:text-foreground",
                  )}
                  aria-label="List view"
                  aria-pressed={view === "list"}
                >
                  <List className="size-4" />
                </button>
              </div>
            </div>

            <p className="text-xs text-subtle-foreground">
              {filtered.length} of {docs.length} document
              {docs.length === 1 ? "" : "s"}
            </p>

            {filtered.length === 0 ? (
              <EmptyState
                icon={Search}
                title="No matches"
                description="Try a different search or filter."
              />
            ) : view === "grid" ? (
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {filtered.map((d) => (
                  <Card
                    key={d.id}
                    className="group relative flex flex-col gap-3 p-4 transition-colors hover:border-border-strong"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex size-10 items-center justify-center rounded-lg bg-primary-muted text-primary">
                        <FileText className="size-5" />
                      </div>
                      <DocMenu id={d.id} onRemove={() => remove(d.id)} />
                    </div>
                    <Link href={`/documents/${d.id}`} className="flex-1">
                      <p className="line-clamp-2 text-sm font-medium group-hover:text-primary">
                        {d.filename}
                      </p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        {d.clauseCount} clauses · {relativeTime(d.uploadedAt)}
                      </p>
                    </Link>
                    <div className="flex flex-wrap items-center gap-1.5">
                      <SensitivityBadge tier={d.sensitivityTier} />
                      {d.tags.map((t) => (
                        <Badge key={t} variant="outline">
                          <TagIcon />
                          {t}
                        </Badge>
                      ))}
                    </div>
                  </Card>
                ))}
              </div>
            ) : (
              <div className="overflow-hidden rounded-xl border border-border">
                <ul className="divide-y divide-border">
                  {filtered.map((d) => (
                    <li
                      key={d.id}
                      className="flex items-center gap-4 px-4 py-3 hover:bg-muted/40"
                    >
                      <FileText className="size-4 shrink-0 text-muted-foreground" />
                      <Link
                        href={`/documents/${d.id}`}
                        className="min-w-0 flex-1"
                      >
                        <p className="truncate text-sm font-medium">
                          {d.filename}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {d.clauseCount} clauses · {relativeTime(d.uploadedAt)}
                        </p>
                      </Link>
                      <SensitivityBadge tier={d.sensitivityTier} />
                      <DocMenu id={d.id} onRemove={() => remove(d.id)} />
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </>
        )}
      </PageBody>
    </>
  );
}

function DocMenu({ id, onRemove }: { id: number; onRemove: () => void }) {
  const addTag = useDocuments((s) => s.addTag);
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon-sm" aria-label="Document actions">
          <span className="text-lg leading-none">⋯</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem asChild>
          <Link href={`/documents/${id}`}>Open workspace</Link>
        </DropdownMenuItem>
        <DropdownMenuItem
          onSelect={(e) => {
            e.preventDefault();
            const t = window.prompt("Add a tag");
            if (t?.trim()) addTag(id, t.trim());
          }}
        >
          <TagIcon /> Add tag
        </DropdownMenuItem>
        <DropdownMenuItem
          variant="danger"
          onClick={() => {
            onRemove();
            toast.success("Removed from library", {
              description: "The document still exists on the backend.",
            });
          }}
        >
          <Trash2 /> Remove from library
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
