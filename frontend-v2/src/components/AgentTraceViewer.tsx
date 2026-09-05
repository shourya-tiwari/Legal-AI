import type { components } from "@/lib/api-types";

type AgentStep = components["schemas"]["AgentStep"];

// docs/v2/TASKS.md's "Agent Trace Viewer" names real-time streaming via a
// session WebSocket, which needs session infrastructure that doesn't exist
// yet (see the Memory Service line item, also not built). This is the
// honest subset that's actually buildable right now: POST .../analyze
// already returns the full step-by-step trace in one response
// (AgentAnalyzeResponse.trace) -- it just had nowhere to render. Post-hoc,
// not live, but a real trace of what each agent actually did.
const AGENT_LABELS: Record<string, string> = {
  extraction: "Extraction",
  planner: "Planner",
  risk_compliance: "Risk & Compliance",
  clause_research: "Clause Research",
  summary: "Summary",
  summarize: "Summary",
  verifier: "Verifier",
};

const AGENT_ICONS: Record<string, string> = {
  extraction: "📄",
  planner: "🧭",
  risk_compliance: "⚠️",
  clause_research: "🔎",
  summary: "📝",
  summarize: "📝",
  verifier: "✅",
};

export function AgentTraceViewer({ trace }: { trace: AgentStep[] }) {
  if (trace.length === 0) {
    return <p className="text-xs text-zinc-500">No trace recorded.</p>;
  }

  return (
    <ol className="flex flex-col">
      {trace.map((step, i) => (
        <li key={i} className="relative flex gap-3 pb-4 last:pb-0">
          {i < trace.length - 1 && (
            <span className="absolute top-7 left-3.5 h-full w-px bg-white/10" aria-hidden="true" />
          )}
          <span className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full bg-indigo-500/15 text-sm">
            {AGENT_ICONS[step.agent_name] ?? "•"}
          </span>
          <div className="pt-0.5">
            <p className="text-xs font-semibold text-zinc-200">
              {AGENT_LABELS[step.agent_name] ?? step.agent_name}
            </p>
            <p className="text-xs text-zinc-500">
              <span className="text-zinc-400">in:</span> {step.input_summary}
            </p>
            <p className="text-xs text-zinc-500">
              <span className="text-zinc-400">out:</span> {step.output_summary}
            </p>
          </div>
        </li>
      ))}
    </ol>
  );
}
