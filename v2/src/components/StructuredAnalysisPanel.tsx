"use client";

import { useMutation } from "@tanstack/react-query";
import { analyzeNlp, type ClauseObject } from "@/lib/api";

const MODALITY_STYLE: Record<string, string> = {
  obligation: "bg-blue-500/15 text-blue-300",
  permission: "bg-emerald-500/15 text-emerald-300",
  prohibition: "bg-red-500/15 text-red-300",
  discretion: "bg-amber-500/15 text-amber-300",
};

// Surfaces app/services/nlp/pipeline.py's structured output (segmentation,
// clause typing, deontic tagging, entities, defined terms, cross-references,
// ambiguity flags) -- a real, tested, eval-gated pipeline (POST /api/nlp/analyze)
// that had no UI anywhere in the project before this.
export function StructuredAnalysisPanel({ fullText }: { fullText: string }) {
  const analyze = useMutation({
    mutationFn: () => analyzeNlp(fullText),
  });

  return (
    <div className="flex flex-col gap-4 rounded-2xl border border-white/10 bg-white/[0.04] p-5 shadow-sm backdrop-blur">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-zinc-300">Structured NLP analysis</h2>
          <p className="text-xs text-zinc-500">
            Clause types, deontic modality, entities, and ambiguity per clause.
          </p>
        </div>
        <button
          type="button"
          onClick={() => analyze.mutate()}
          disabled={analyze.isPending}
          className="rounded-full bg-zinc-900 px-4 py-1.5 text-sm font-semibold text-white transition-colors hover:bg-zinc-800 disabled:opacity-50"
        >
          {analyze.isPending ? "Analyzing…" : "Run structured analysis"}
        </button>
      </div>

      {analyze.isError && (
        <p role="alert" className="text-sm text-red-400">
          Error: {analyze.error instanceof Error ? analyze.error.message : String(analyze.error)}
        </p>
      )}

      {analyze.data && (
        <ul className="flex max-h-[32rem] flex-col gap-2 overflow-y-auto">
          {(analyze.data.clauses ?? []).map((clause) => (
            <ClauseRow key={clause.id} clause={clause} />
          ))}
        </ul>
      )}
    </div>
  );
}

function ClauseRow({ clause }: { clause: ClauseObject }) {
  const entities = clause.entities ?? [];
  const deonticTags = clause.deontic_tags ?? [];
  const definedTerms = clause.defined_terms_used ?? [];
  const ambiguity = clause.ambiguity_flags ?? [];
  const crossRefs = clause.cross_references ?? [];

  return (
    <li className="rounded-xl border border-white/10 bg-white/[0.02] p-3">
      <div className="mb-1.5 flex flex-wrap items-center gap-1.5">
        <span className="rounded-full bg-indigo-500/15 px-2 py-0.5 text-[11px] font-medium text-indigo-300">
          {clause.clause_type}
          {clause.clause_type_source === "ai" && " · ai"}
        </span>
        {deonticTags.map((tag, i) => (
          <span
            key={i}
            className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${MODALITY_STYLE[tag.modality] ?? "bg-white/10 text-zinc-300"}`}
          >
            {tag.modality}
          </span>
        ))}
        {ambiguity.length > 0 && (
          <span className="rounded-full bg-amber-500/15 px-2 py-0.5 text-[11px] font-medium text-amber-300">
            {ambiguity.length} ambiguity flag{ambiguity.length > 1 ? "s" : ""}
          </span>
        )}
      </div>

      <p className="line-clamp-2 text-sm text-zinc-300">{clause.text}</p>

      {(entities.length > 0 || definedTerms.length > 0 || crossRefs.length > 0) && (
        <div className="mt-2 flex flex-wrap gap-1 text-[11px] text-zinc-500">
          {entities.map((e, i) => (
            <span key={`e-${i}`} className="rounded bg-white/5 px-1.5 py-0.5">
              {e.type}: {e.text}
            </span>
          ))}
          {definedTerms.map((t, i) => (
            <span key={`d-${i}`} className="rounded bg-white/5 px-1.5 py-0.5">
              term: {t}
            </span>
          ))}
          {crossRefs.map((r, i) => (
            <span key={`r-${i}`} className="rounded bg-white/5 px-1.5 py-0.5">
              ref: {r.text}
            </span>
          ))}
        </div>
      )}

      {ambiguity.length > 0 && (
        <ul className="mt-1.5 flex flex-col gap-0.5">
          {ambiguity.map((a, i) => (
            <li key={i} className="text-[11px] text-amber-400">
              ⚠ {a.term} — {a.explanation}
            </li>
          ))}
        </ul>
      )}
    </li>
  );
}
