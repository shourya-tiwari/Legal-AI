"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { simulateTimeline } from "@/lib/api";

const STATUS_STYLE: Record<string, string> = {
  past: "bg-white/10 text-zinc-400",
  upcoming: "bg-amber-500/15 text-amber-300",
  future: "bg-blue-500/15 text-blue-300",
};

// docs/v2/ROADMAP.md Phase 8: "Simulation agent (deterministic discrete-event
// baseline -> Monte-Carlo NOVELTY.md #2)". Every clause with a resolved
// absolute date becomes a scheduled event, classified past/upcoming/future
// relative to a reference date -- no conditional-trigger graph or
// portfolio-scope emergent risk yet (needs KG schema this project doesn't
// have), just a real, honest single-document timeline.
export function SimulationPanel({ documentId }: { documentId: number }) {
  const [warningWindow, setWarningWindow] = useState(30);
  const simulate = useMutation({
    mutationFn: () => simulateTimeline(documentId, { warning_window_days: warningWindow }),
  });

  return (
    <div className="flex flex-col gap-4 rounded-2xl border border-white/10 bg-white/[0.04] p-5 shadow-sm backdrop-blur">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold text-zinc-300">Obligation timeline simulation</h2>
          <p className="text-xs text-zinc-500">
            Every resolved date in this document, classified against today — a deterministic
            baseline, not a prediction.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <label className="text-xs text-zinc-500" htmlFor="warning-window">
            Warning window (days)
          </label>
          <input
            id="warning-window"
            type="number"
            min={1}
            max={365}
            value={warningWindow}
            onChange={(e) => setWarningWindow(Number(e.target.value) || 30)}
            className="w-16 rounded-md border border-zinc-700 bg-zinc-900 px-2 py-1 text-sm text-zinc-100"
          />
          <button
            type="button"
            onClick={() => simulate.mutate()}
            disabled={simulate.isPending}
            className="rounded-full bg-zinc-900 px-4 py-1.5 text-sm font-semibold text-white transition-colors hover:bg-zinc-800 disabled:opacity-50"
          >
            {simulate.isPending ? "Simulating…" : "Run simulation"}
          </button>
        </div>
      </div>

      {simulate.isError && (
        <p role="alert" className="text-sm text-red-400">
          Error: {simulate.error instanceof Error ? simulate.error.message : String(simulate.error)}
        </p>
      )}

      {simulate.data && (
        <div className="flex flex-col gap-2">
          <p className="text-xs text-zinc-500">
            Reference date: {simulate.data.reference_date} · window: {simulate.data.warning_window_days} days
          </p>
          {(simulate.data.events ?? []).length === 0 ? (
            <p className="text-xs text-zinc-500">
              No clauses with a resolvable absolute date were found (bare durations like &quot;30
              days&quot; are honestly skipped, not guessed against today).
            </p>
          ) : (
            <ol className="flex flex-col gap-2">
              {(simulate.data.events ?? []).map((e, i) => (
                <li
                  key={i}
                  className="flex flex-col gap-1 rounded-lg border border-white/10 bg-white/[0.02] p-2.5 text-xs sm:flex-row sm:items-start sm:gap-3"
                >
                  <div className="flex flex-shrink-0 items-center gap-2 sm:w-40">
                    <span className={`rounded-full px-2 py-0.5 font-medium ${STATUS_STYLE[e.status] ?? "bg-white/10 text-zinc-300"}`}>
                      {e.status}
                    </span>
                    <span className="font-mono text-zinc-400">{e.date}</span>
                  </div>
                  <div>
                    <p className="text-zinc-300">
                      <span className="text-zinc-500">[{e.clause_type}{e.modality !== "none" ? ` · ${e.modality}` : ""}]</span>{" "}
                      {e.clause_text}
                    </p>
                  </div>
                </li>
              ))}
            </ol>
          )}
        </div>
      )}
    </div>
  );
}
