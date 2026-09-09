"use client";

import { useQuery } from "@tanstack/react-query";
import { getModelsStatus, getEvalRuns } from "@/lib/api";
import { SiteHeader } from "@/components/SiteHeader";

const CLASS_STYLE: Record<string, string> = {
  A: "bg-emerald-500/15 text-emerald-300",
  B: "bg-blue-500/15 text-blue-300",
  C: "bg-amber-500/15 text-amber-300",
};

const CLASS_LABEL: Record<string, string> = {
  A: "A · deterministic/CPU",
  B: "B · self-hosted neural",
  C: "C · external API",
};

export default function ModelsStatusPage() {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["models-status"],
    queryFn: getModelsStatus,
  });

  const { data: evalData } = useQuery({
    queryKey: ["eval-runs"],
    queryFn: getEvalRuns,
  });

  return (
    <div className="flex flex-1 flex-col">
      <SiteHeader />

      <main className="mx-auto w-full max-w-4xl flex-1 px-6 py-16">
        <h1 className="text-3xl font-semibold tracking-tight text-white">Model Router</h1>
        <p className="mt-2 max-w-xl text-sm text-zinc-400">
          Every AI call in this app goes through the Model Router — no service imports a vendor
          SDK directly. This is the operator&apos;s view of the registered providers, live from{" "}
          <code className="rounded bg-white/10 px-1 py-0.5 text-xs">GET /api/models/status</code>.
        </p>

        {data && (
          <div className="mt-6 flex flex-wrap gap-2 text-xs">
            <span className="rounded-full bg-white/10 px-2.5 py-1 font-medium text-zinc-300">
              policy v{data.policy_version}
            </span>
            <span
              className={`rounded-full px-2.5 py-1 font-medium ${
                data.external_providers_enabled
                  ? "bg-amber-500/15 text-amber-300"
                  : "bg-emerald-500/15 text-emerald-300"
              }`}
            >
              external providers {data.external_providers_enabled ? "enabled" : "disabled"}
            </span>
            <span
              className={`rounded-full px-2.5 py-1 font-medium ${
                data.strict_local_only
                  ? "bg-emerald-500/15 text-emerald-300"
                  : "bg-white/10 text-zinc-300"
              }`}
            >
              strict local only: {String(data.strict_local_only)}
            </span>
          </div>
        )}

        {isLoading && <p className="mt-8 text-sm text-zinc-500">Loading provider registry…</p>}
        {isError && (
          <p role="alert" className="mt-8 text-sm text-red-400">
            Error: {error instanceof Error ? error.message : String(error)}
          </p>
        )}

        {data && (
          <div className="mt-8 flex flex-col gap-3">
            {(data.providers ?? []).map((p) => (
              <div
                key={p.name}
                className="flex flex-col gap-2 rounded-2xl border border-white/10 bg-white/[0.04] p-4 backdrop-blur sm:flex-row sm:items-center sm:justify-between"
              >
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-sm font-semibold text-zinc-100">{p.name}</span>
                    <span
                      className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${CLASS_STYLE[p.hosting_class] ?? "bg-white/10 text-zinc-300"}`}
                    >
                      {CLASS_LABEL[p.hosting_class] ?? p.hosting_class}
                    </span>
                    {p.leaves_perimeter && (
                      <span className="rounded-full bg-red-500/15 px-2 py-0.5 text-[11px] font-medium text-red-300">
                        leaves perimeter
                      </span>
                    )}
                  </div>
                  <p className="mt-1 text-xs text-zinc-500">
                    {(p.capabilities ?? []).join(", ") || "no capabilities"}
                    {p.models && p.models.length > 0 ? ` — ${p.models.join(", ")}` : ""}
                  </p>
                  {p.note && <p className="mt-1 text-xs text-zinc-500 italic">{p.note}</p>}
                </div>
                <span
                  className={`self-start rounded-full px-2.5 py-1 text-xs font-semibold sm:self-center ${
                    p.available
                      ? "bg-emerald-500/15 text-emerald-300"
                      : "bg-white/10 text-zinc-500"
                  }`}
                >
                  {p.available ? "available" : "not available"}
                </span>
              </div>
            ))}
          </div>
        )}

        <h2 className="mt-14 text-xl font-semibold text-white">Eval scores behind the policy</h2>
        <p className="mt-2 max-w-xl text-sm text-zinc-400">
          The cutover gate&apos;s evidence for whether a self-hosted model actually beats the
          Gemini baseline for a task — most recent run per task/provider, from{" "}
          <code className="rounded bg-white/10 px-1 py-0.5 text-xs">GET /api/models/eval-runs</code>.
        </p>

        {evalData && (evalData.runs ?? []).length === 0 && (
          <p className="mt-6 text-sm text-zinc-500">
            No eval runs recorded yet — run <code className="rounded bg-white/10 px-1 py-0.5 text-xs">
            python -m app.eval.cutover_gate</code> against a served model to populate this.
          </p>
        )}

        {evalData && (evalData.runs ?? []).length > 0 && (
          <div className="mt-6 overflow-x-auto rounded-2xl border border-white/10 bg-white/[0.04] backdrop-blur">
            <table className="w-full min-w-[640px] text-left text-sm">
              <thead>
                <tr className="border-b border-white/10 text-xs uppercase tracking-wide text-zinc-500">
                  <th className="px-4 py-3 font-medium">Task</th>
                  <th className="px-4 py-3 font-medium">Provider</th>
                  <th className="px-4 py-3 font-medium">Model</th>
                  <th className="px-4 py-3 font-medium">Score</th>
                  <th className="px-4 py-3 font-medium">Baseline</th>
                  <th className="px-4 py-3 font-medium">Verdict</th>
                </tr>
              </thead>
              <tbody>
                {(evalData.runs ?? []).map((r, i) => (
                  <tr key={i} className="border-b border-white/5 last:border-0">
                    <td className="px-4 py-3 font-mono text-zinc-200">{r.task}</td>
                    <td className="px-4 py-3 text-zinc-300">{r.provider}</td>
                    <td className="px-4 py-3 text-zinc-400">{r.model}</td>
                    <td className="px-4 py-3 text-zinc-200">
                      {r.score.toFixed(3)} <span className="text-zinc-500">({r.metric}, n={r.n_examples})</span>
                    </td>
                    <td className="px-4 py-3 text-zinc-400">
                      {r.baseline_score != null ? r.baseline_score.toFixed(3) : "—"}
                    </td>
                    <td className="px-4 py-3">
                      {r.passed === true && (
                        <span className="rounded-full bg-emerald-500/15 px-2 py-0.5 text-xs font-medium text-emerald-300">
                          ✅ pass
                        </span>
                      )}
                      {r.passed === false && (
                        <span className="rounded-full bg-red-500/15 px-2 py-0.5 text-xs font-medium text-red-300">
                          ❌ fail
                        </span>
                      )}
                      {r.passed == null && <span className="text-xs text-zinc-500">—</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </main>
    </div>
  );
}
