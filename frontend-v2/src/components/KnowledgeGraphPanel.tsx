"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { ingestKg, queryKgConflicts, queryKgTerm } from "@/lib/api";

// Surfaces the Memgraph-backed knowledge graph (app/services/kg/) -- ingest
// a document's defined terms + clauses, then ask "what else references this
// term" and "does anything conflict with it across documents." Real,
// tested backend capability (POST /api/kg/ingest|query|conflicts) with no
// UI anywhere in the project before this.
export function KnowledgeGraphPanel({ documentId }: { documentId: number }) {
  const [term, setTerm] = useState("");

  const ingest = useMutation({ mutationFn: () => ingestKg(documentId) });
  const query = useMutation({ mutationFn: (t: string) => queryKgTerm(t) });
  const conflicts = useMutation({ mutationFn: (t: string) => queryKgConflicts(t) });

  const kgUnavailable = ingest.data && !ingest.data.kg_available;

  return (
    <div className="flex flex-col gap-4 rounded-2xl border border-white/10 bg-white/[0.04] p-5 shadow-sm backdrop-blur">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-zinc-300">Knowledge graph</h2>
          <p className="text-xs text-zinc-500">
            Ingest this document, then search a defined term for cross-document usage and conflicts.
          </p>
        </div>
        <button
          type="button"
          onClick={() => ingest.mutate()}
          disabled={ingest.isPending}
          className="rounded-full bg-zinc-900 px-4 py-1.5 text-sm font-semibold text-white transition-colors hover:bg-zinc-800 disabled:opacity-50"
        >
          {ingest.isPending ? "Ingesting…" : "Ingest into graph"}
        </button>
      </div>

      {ingest.isError && (
        <p role="alert" className="text-sm text-red-400">
          Error: {ingest.error instanceof Error ? ingest.error.message : String(ingest.error)}
        </p>
      )}

      {ingest.data && (
        <div className="flex flex-wrap gap-2 text-xs">
          <span className="rounded-full bg-white/10 px-2 py-1 font-medium text-zinc-300">
            {ingest.data.clauses} clauses
          </span>
          <span className="rounded-full bg-white/10 px-2 py-1 font-medium text-zinc-300">
            {ingest.data.defined_terms} defined terms
          </span>
          <span className="rounded-full bg-white/10 px-2 py-1 font-medium text-zinc-300">
            {ingest.data.cross_references} cross-references
          </span>
          <span className="rounded-full bg-white/10 px-2 py-1 font-medium text-zinc-300">
            {ingest.data.portfolio_links_created} portfolio links
          </span>
          {kgUnavailable && (
            <span className="rounded-full bg-amber-500/15 px-2 py-1 font-medium text-amber-300">
              Memgraph unreachable — ingest no-oped (fail-soft)
            </span>
          )}
        </div>
      )}

      <form
        className="flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          const t = term.trim();
          if (!t) return;
          query.mutate(t);
          conflicts.mutate(t);
        }}
      >
        <input
          className="flex-1 rounded-full border border-zinc-700 bg-zinc-900 px-3.5 py-1.5 text-sm text-zinc-100 placeholder:text-zinc-500 focus:border-indigo-400/50 focus:outline-none"
          placeholder='Defined term, e.g. "the Company"'
          value={term}
          onChange={(e) => setTerm(e.target.value)}
        />
        <button
          type="submit"
          disabled={!term.trim() || query.isPending || conflicts.isPending}
          className="rounded-full bg-gradient-to-r from-indigo-500 to-blue-500 px-4 py-1.5 text-sm font-semibold text-white shadow-sm shadow-indigo-950 transition-transform hover:scale-[1.03] disabled:opacity-50 disabled:from-zinc-700 disabled:to-zinc-700 disabled:shadow-none"
        >
          Search
        </button>
      </form>

      {query.data && (
        <div className="rounded-xl border border-white/10 bg-white/[0.04] p-3">
          <h4 className="mb-1 text-xs font-semibold uppercase tracking-wide text-zinc-500">
            Clauses using &quot;{query.data.term}&quot; ({(query.data.clauses ?? []).length})
          </h4>
          {(query.data.clauses ?? []).length > 0 ? (
            <ul className="flex flex-col gap-1 text-xs text-zinc-300">
              {(query.data.clauses ?? []).map((c, i) => (
                <li key={i}>{JSON.stringify(c)}</li>
              ))}
            </ul>
          ) : (
            <p className="text-xs text-zinc-500">No clauses found for this term.</p>
          )}
        </div>
      )}

      {conflicts.data && (conflicts.data.conflicts ?? []).length > 0 && (
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-3">
          <h4 className="mb-1 text-xs font-semibold uppercase tracking-wide text-red-400">
            Candidate conflicts ({(conflicts.data.conflicts ?? []).length})
          </h4>
          <ul className="flex flex-col gap-1 text-xs text-red-300">
            {(conflicts.data.conflicts ?? []).map((c, i) => (
              <li key={i}>{JSON.stringify(c)}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
