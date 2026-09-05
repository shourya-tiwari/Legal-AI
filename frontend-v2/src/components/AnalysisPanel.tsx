"use client";

import { useMutation } from "@tanstack/react-query";
import { analyzeDocument } from "@/lib/api";

// The planner-driven agent pipeline (app/agents/graph.py) has no UI anywhere
// in the project yet -- this is pure bonus: the backend already returns
// everything needed to render it (plan, trace, risk findings, KG conflicts,
// faithfulness), so surfacing it here is zero backend work.
export function AnalysisPanel({ documentId }: { documentId: number }) {
  const analyze = useMutation({
    mutationFn: () => analyzeDocument(documentId, { analysis_mode: "full" }),
  });

  return (
    <div className="flex flex-col gap-4 rounded-2xl border border-white/10 bg-white/[0.04] p-5 shadow-sm backdrop-blur">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-zinc-300">
          Full agent analysis
        </h2>
        <button
          type="button"
          onClick={() => analyze.mutate()}
          disabled={analyze.isPending}
          className="rounded-full bg-zinc-900 px-4 py-1.5 text-sm font-semibold text-white transition-colors hover:bg-zinc-800 disabled:opacity-50"
        >
          {analyze.isPending ? "Running planner + agents…" : "Run full analysis"}
        </button>
      </div>

      {analyze.isError && (
        <p role="alert" className="text-sm text-red-400">
          Error: {analyze.error instanceof Error ? analyze.error.message : String(analyze.error)}
        </p>
      )}

      {analyze.data && (
        <div className="flex flex-col gap-3">
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <span className="rounded-full bg-white/10 px-2 py-1 font-medium text-zinc-300">
              plan: {(analyze.data.plan ?? []).join(" → ")}
            </span>
            {analyze.data.needs_human_review && (
              <span className="rounded-full bg-red-500/15 px-2 py-1 font-medium text-red-300">
                needs human review
              </span>
            )}
            <span
              className={`rounded-full px-2 py-1 font-medium ${
                analyze.data.faithfulness_ok
                  ? "bg-emerald-500/15 text-emerald-300"
                  : "bg-amber-500/15 text-amber-300"
              }`}
            >
              faithfulness: {analyze.data.faithfulness_ok ? "ok" : "issues found"} (
              {analyze.data.faithfulness_method})
            </span>
          </div>

          {analyze.data.plan_rationale && (
            <p className="text-xs italic text-zinc-500">{analyze.data.plan_rationale}</p>
          )}

          <div className="rounded-xl border border-white/10 bg-white/[0.04] p-3">
            <h4 className="mb-1 text-xs font-semibold uppercase tracking-wide text-zinc-500">
              Summary
            </h4>
            <p className="whitespace-pre-wrap text-sm text-zinc-200">{analyze.data.summary}</p>
          </div>

          {(analyze.data.unsupported_claims ?? []).length > 0 && (
            <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-3">
              <h4 className="mb-1 text-xs font-semibold uppercase tracking-wide text-amber-400">
                Unsupported claims
              </h4>
              <ul className="list-disc pl-5 text-xs text-amber-300">
                {(analyze.data.unsupported_claims ?? []).map((c, i) => (
                  <li key={i}>{c}</li>
                ))}
              </ul>
            </div>
          )}

          {(analyze.data.risk_findings ?? []).length > 0 && (
            <div className="rounded-xl border border-white/10 bg-white/[0.04] p-3">
              <h4 className="mb-1 text-xs font-semibold uppercase tracking-wide text-zinc-500">
                Risk findings ({(analyze.data.risk_findings ?? []).length})
              </h4>
              <ul className="flex flex-col gap-1 text-xs text-zinc-300">
                {(analyze.data.risk_findings ?? []).map((f, i) => (
                  <li key={i}>{JSON.stringify(f)}</li>
                ))}
              </ul>
            </div>
          )}

          {(analyze.data.kg_conflicts ?? []).length > 0 && (
            <div className="rounded-md border border-red-500/30 bg-red-500/10 p-3">
              <h4 className="mb-1 text-xs font-semibold uppercase tracking-wide text-red-400">
                Knowledge-graph conflicts ({(analyze.data.kg_conflicts ?? []).length})
              </h4>
              <ul className="flex flex-col gap-1 text-xs text-red-300">
                {(analyze.data.kg_conflicts ?? []).map((c, i) => (
                  <li key={i}>{JSON.stringify(c)}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
