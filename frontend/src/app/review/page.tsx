"use client";

import { useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getReviewQueue, resolveReviewItem, type ReviewQueueItem } from "@/lib/api";
import { SiteHeader } from "@/components/SiteHeader";

// docs/v2/ROADMAP.md Phase 7: "human-in-the-loop review queue UI." The
// analyze() endpoint always computed needs_human_review but never persisted
// it -- app/routes/review.py + the new CaseAnalysis table (LEARNING_LOG.md
// #32) is what makes a real queue possible here.
export default function ReviewQueuePage() {
  const [includeResolved, setIncludeResolved] = useState(false);
  const queryClient = useQueryClient();

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["review-queue", includeResolved],
    queryFn: () => getReviewQueue(includeResolved),
  });

  return (
    <div className="flex flex-1 flex-col">
      <SiteHeader />

      <main className="mx-auto w-full max-w-4xl flex-1 px-6 py-16">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-3xl font-semibold tracking-tight text-white">Review queue</h1>
            <p className="mt-2 max-w-xl text-sm text-zinc-400">
              Every agent analysis the Verifier flagged <code className="rounded bg-white/10 px-1 py-0.5 text-xs">needs_human_review</code> — a
              KG conflict, an invalid citation, or a faithfulness check that failed.
            </p>
          </div>
          <label className="flex items-center gap-2 text-xs text-zinc-400">
            <input
              type="checkbox"
              checked={includeResolved}
              onChange={(e) => setIncludeResolved(e.target.checked)}
              className="h-4 w-4 rounded border-zinc-700 bg-zinc-900"
            />
            Show resolved
          </label>
        </div>

        {isLoading && <p className="mt-8 text-sm text-zinc-500">Loading queue…</p>}
        {isError && (
          <p role="alert" className="mt-8 text-sm text-red-400">
            Error: {error instanceof Error ? error.message : String(error)}
          </p>
        )}

        {data && (data.items ?? []).length === 0 && (
          <p className="mt-8 text-sm text-zinc-500">
            {includeResolved ? "No analyses have ever been flagged." : "Nothing needs review right now."}
          </p>
        )}

        <div className="mt-8 flex flex-col gap-4">
          {(data?.items ?? []).map((item) => (
            <ReviewCard
              key={item.id}
              item={item}
              onResolved={() => queryClient.invalidateQueries({ queryKey: ["review-queue"] })}
            />
          ))}
        </div>
      </main>
    </div>
  );
}

function ReviewCard({ item, onResolved }: { item: ReviewQueueItem; onResolved: () => void }) {
  const [note, setNote] = useState("");
  const resolve = useMutation({
    mutationFn: () => resolveReviewItem(item.id, note.trim() || undefined),
    onSuccess: onResolved,
  });

  return (
    <div className="flex flex-col gap-3 rounded-2xl border border-white/10 bg-white/[0.04] p-5 shadow-sm backdrop-blur">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Link href={`/documents/${item.document_id}`} className="text-sm font-semibold text-indigo-400 hover:underline">
            {item.document_filename}
          </Link>
          <span className="text-xs text-zinc-500">{item.created_at?.slice(0, 10)}</span>
        </div>
        {item.reviewed ? (
          <span className="rounded-full bg-emerald-500/15 px-2.5 py-1 text-xs font-medium text-emerald-300">
            reviewed{item.reviewed_at ? ` ${item.reviewed_at.slice(0, 10)}` : ""}
          </span>
        ) : (
          <span className="rounded-full bg-red-500/15 px-2.5 py-1 text-xs font-medium text-red-300">
            needs review
          </span>
        )}
      </div>

      <p className="text-sm text-zinc-300">{item.summary}</p>

      <div className="flex flex-wrap gap-2 text-xs">
        <span
          className={`rounded-full px-2 py-0.5 font-medium ${
            item.faithfulness_ok ? "bg-emerald-500/15 text-emerald-300" : "bg-amber-500/15 text-amber-300"
          }`}
        >
          faithfulness: {item.faithfulness_ok ? "ok" : "issues"} ({item.faithfulness_method})
        </span>
        {(item.invalid_citation_numbers ?? []).length > 0 && (
          <span className="rounded-full bg-red-500/15 px-2 py-0.5 font-medium text-red-300">
            invalid citations: {(item.invalid_citation_numbers ?? []).join(", ")}
          </span>
        )}
        {(item.unsupported_claims ?? []).length > 0 && (
          <span className="rounded-full bg-amber-500/15 px-2 py-0.5 font-medium text-amber-300">
            {(item.unsupported_claims ?? []).length} unsupported claim{(item.unsupported_claims ?? []).length > 1 ? "s" : ""}
          </span>
        )}
      </div>

      {item.reviewed ? (
        item.reviewer_note && <p className="text-xs italic text-zinc-500">Note: {item.reviewer_note}</p>
      ) : (
        <div className="flex gap-2">
          <input
            className="flex-1 rounded-full border border-zinc-700 bg-zinc-900 px-3.5 py-1.5 text-xs text-zinc-100 placeholder:text-zinc-500 focus:border-indigo-400/50 focus:outline-none"
            placeholder="Optional note (what you checked)…"
            value={note}
            onChange={(e) => setNote(e.target.value)}
          />
          <button
            type="button"
            onClick={() => resolve.mutate()}
            disabled={resolve.isPending}
            className="rounded-full bg-zinc-900 px-4 py-1.5 text-xs font-semibold text-white transition-colors hover:bg-zinc-800 disabled:opacity-50"
          >
            {resolve.isPending ? "Marking…" : "Mark reviewed"}
          </button>
        </div>
      )}
      {resolve.isError && (
        <p role="alert" className="text-xs text-red-400">
          Error: {resolve.error instanceof Error ? resolve.error.message : String(resolve.error)}
        </p>
      )}
    </div>
  );
}
