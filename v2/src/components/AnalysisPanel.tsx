"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { analyzeDocument } from "@/lib/api";
import { AgentTraceViewer } from "@/components/AgentTraceViewer";

// The planner-driven agent pipeline (app/agents/graph.py) has no UI anywhere
// in the project yet -- this is pure bonus: the backend already returns
// everything needed to render it (plan, trace, risk findings, KG conflicts,
// faithfulness), so surfacing it here is zero backend work.
export function AnalysisPanel({ documentId }: { documentId: number }) {
  const [showTrace, setShowTrace] = useState(false);
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
            <button
              type="button"
              onClick={() => setShowTrace((v) => !v)}
              className="flex w-full items-center justify-between text-left text-xs font-semibold uppercase tracking-wide text-zinc-500"
            >
              Agent trace ({(analyze.data.trace ?? []).length} steps)
              <span aria-hidden="true">{showTrace ? "▲" : "▼"}</span>
            </button>
            {showTrace && (
              <div className="mt-3">
                <AgentTraceViewer trace={analyze.data.trace ?? []} />
              </div>
            )}
          </div>

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

          {/* Negotiation/Drafting agent (app/agents/negotiation.py) -- clauses
              deviating from the org's configured preferred language. Always
              status="pending_review"; never auto-applied. Empty unless the org
              has set Organization.negotiation_preferences. This is the
              non-collaborative "Negotiation Studio" surface -- the Yjs
              real-time collaborative editor is deferred (needs a WebSocket
              sync server this deployment can't validate; docs/v2/TASKS.md). */}
          {(analyze.data.negotiation_suggestions ?? []).length > 0 && (
            <div className="rounded-xl border border-sky-500/30 bg-sky-500/10 p-3">
              <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-sky-300">
                Negotiation suggestions ({(analyze.data.negotiation_suggestions ?? []).length}) — pending review
              </h4>
              <ul className="flex flex-col gap-3 text-xs">
                {(analyze.data.negotiation_suggestions ?? []).map((s, i) => (
                  <li key={i} className="rounded-lg border border-white/10 bg-white/[0.03] p-2">
                    <div className="mb-1 flex flex-wrap items-center gap-2 text-[11px] text-zinc-400">
                      <span className="rounded-full bg-white/10 px-2 py-0.5 font-medium text-zinc-200">
                        {s.clause_type}
                      </span>
                      <span>clause {String(s.clause_id)}</span>
                      <span>similarity {(s.similarity * 100).toFixed(0)}%</span>
                      <span className="rounded-full bg-amber-500/15 px-2 py-0.5 text-amber-300">
                        {s.status}
                      </span>
                    </div>
                    {s.rationale && <p className="mb-1 italic text-zinc-400">{s.rationale}</p>}
                    <pre className="overflow-x-auto whitespace-pre-wrap rounded bg-black/30 p-2 text-[11px] leading-relaxed text-zinc-300">
                      {(s.diff_lines ?? []).join("\n")}
                    </pre>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
