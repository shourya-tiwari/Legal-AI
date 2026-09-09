"use client";

import { useMutation } from "@tanstack/react-query";
import { checkConsistency, type ConsistencyResponse } from "@/lib/api";

type ConsistencyFinding = NonNullable<ConsistencyResponse["findings"]>[number];

// docs/v2/ROADMAP.md Phase 8: "Cross-Document Consistency agent
// (embedding-similarity baseline -> learned NOVELTY.md #1)". Finds clauses
// across the org's other documents that are semantically similar to a
// clause here but phrased differently (so the exact-term KG conflict check
// can't see them), and flags the ones whose deontic modality actively
// conflicts (e.g. an obligation here, a prohibition on the similar clause
// elsewhere). A candidate for review, not a confirmed contradiction --
// actor/action resolution isn't built, same limitation as the KG check.
export function ConsistencyPanel({ documentId }: { documentId: number }) {
  const check = useMutation({
    mutationFn: () => checkConsistency(documentId),
  });

  const conflicts = (check.data?.findings ?? []).filter((f) => f.is_conflict);
  const similarOnly = (check.data?.findings ?? []).filter((f) => !f.is_conflict);

  return (
    <div className="flex flex-col gap-4 rounded-2xl border border-white/10 bg-white/[0.04] p-5 shadow-sm backdrop-blur">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-zinc-300">Cross-document consistency</h2>
          <p className="text-xs text-zinc-500">
            Embedding-similarity baseline — checks this document&apos;s obligations/permissions/
            prohibitions against every other document in the org, even when they don&apos;t share
            an exact defined term.
          </p>
        </div>
        <button
          type="button"
          onClick={() => check.mutate()}
          disabled={check.isPending}
          className="rounded-full bg-zinc-900 px-4 py-1.5 text-sm font-semibold text-white transition-colors hover:bg-zinc-800 disabled:opacity-50"
        >
          {check.isPending ? "Checking…" : "Check consistency"}
        </button>
      </div>

      {check.isError && (
        <p role="alert" className="text-sm text-red-400">
          Error: {check.error instanceof Error ? check.error.message : String(check.error)}
        </p>
      )}

      {check.data && (
        <div className="flex flex-col gap-3">
          <p className="text-xs text-zinc-500">
            Checked against {check.data.other_documents_checked} other document
            {check.data.other_documents_checked === 1 ? "" : "s"}.
          </p>

          {conflicts.length > 0 && (
            <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-3">
              <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-red-400">
                Candidate conflicts ({conflicts.length})
              </h4>
              <ul className="flex flex-col gap-3">
                {conflicts.map((f, i) => (
                  <FindingRow key={i} finding={f} />
                ))}
              </ul>
            </div>
          )}

          {similarOnly.length > 0 && (
            <div className="rounded-xl border border-white/10 bg-white/[0.04] p-3">
              <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-zinc-500">
                Similar, same modality ({similarOnly.length})
              </h4>
              <ul className="flex flex-col gap-3">
                {similarOnly.map((f, i) => (
                  <FindingRow key={i} finding={f} />
                ))}
              </ul>
            </div>
          )}

          {conflicts.length === 0 && similarOnly.length === 0 && (
            <p className="text-xs text-zinc-500">
              No similar cross-document clauses found above the similarity threshold.
            </p>
          )}
        </div>
      )}
    </div>
  );
}

function FindingRow({ finding }: { finding: ConsistencyFinding }) {
  return (
    <li className="rounded-lg border border-white/10 bg-white/[0.02] p-2.5 text-xs">
      <div className="mb-1 flex flex-wrap items-center gap-1.5">
        <span className="rounded-full bg-white/10 px-2 py-0.5 font-medium text-zinc-300">
          {finding.modality}
        </span>
        <span className="text-zinc-500">vs</span>
        <span
          className={`rounded-full px-2 py-0.5 font-medium ${
            finding.is_conflict ? "bg-red-500/15 text-red-300" : "bg-white/10 text-zinc-300"
          }`}
        >
          {finding.other_modality}
        </span>
        <span className="ml-auto text-zinc-500">
          {(finding.similarity * 100).toFixed(0)}% similar
        </span>
      </div>
      <p className="text-zinc-300">{finding.clause_text}</p>
      <p className="mt-1 text-zinc-500">
        <span className="font-medium text-zinc-400">{finding.other_document_filename}:</span>{" "}
        {finding.other_clause_text}
      </p>
    </li>
  );
}
