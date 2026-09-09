"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import {
  rewriteDocument,
  riskScanDocument,
  contextualizeDocument,
  type ContextualizeContext,
} from "@/lib/api";
import type { Block } from "@/components/ClauseList";
import { ContextualizeForm } from "@/components/ContextualizeForm";

export function ClauseActions({
  documentId,
  block,
}: {
  documentId: number;
  block: Block;
}) {
  const [showContextForm, setShowContextForm] = useState(false);

  const rewrite = useMutation({
    mutationFn: () => rewriteDocument(documentId, block.id),
  });
  const riskScan = useMutation({
    mutationFn: () => riskScanDocument(documentId, block.id),
  });
  const contextualize = useMutation({
    mutationFn: (context: ContextualizeContext) =>
      contextualizeDocument(documentId, block.id, context),
  });

  return (
    <div className="flex flex-col gap-4 rounded-2xl border border-white/10 bg-white/[0.04] p-5 shadow-sm backdrop-blur">
      <div>
        <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-zinc-500">
          Selected clause
        </h3>
        <p className="whitespace-pre-wrap text-sm text-zinc-200">{block.text}</p>
      </div>

      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => rewrite.mutate()}
          disabled={rewrite.isPending}
          className="rounded-full border border-zinc-700 bg-zinc-900 px-3.5 py-1.5 text-sm font-medium text-zinc-300 transition-colors hover:border-indigo-400/50 hover:bg-indigo-500/10 hover:text-indigo-300 disabled:opacity-50"
        >
          {rewrite.isPending ? "Rewriting…" : "Rewrite this clause"}
        </button>
        <button
          type="button"
          onClick={() => riskScan.mutate()}
          disabled={riskScan.isPending}
          className="rounded-full border border-zinc-700 bg-zinc-900 px-3.5 py-1.5 text-sm font-medium text-zinc-300 transition-colors hover:border-indigo-400/50 hover:bg-indigo-500/10 hover:text-indigo-300 disabled:opacity-50"
        >
          {riskScan.isPending ? "Scanning…" : "Risk-scan this clause"}
        </button>
        <button
          type="button"
          onClick={() => setShowContextForm((v) => !v)}
          className="rounded-full border border-zinc-700 bg-zinc-900 px-3.5 py-1.5 text-sm font-medium text-zinc-300 transition-colors hover:border-indigo-400/50 hover:bg-indigo-500/10 hover:text-indigo-300"
        >
          Contextualize this clause
        </button>
      </div>

      {showContextForm && (
        <ContextualizeForm
          pending={contextualize.isPending}
          onSubmit={(context) => contextualize.mutate(context)}
        />
      )}

      {rewrite.data && (
        <ResultBlock title="Plain-English rewrite">
          <p className="whitespace-pre-wrap text-sm text-zinc-200">
            {rewrite.data.rewritten_text}
          </p>
        </ResultBlock>
      )}
      {rewrite.isError && <ErrorBlock error={rewrite.error} />}

      {riskScan.data && (
        <ResultBlock title="Risk scan">
          <RiskScanResult data={riskScan.data} />
        </ResultBlock>
      )}
      {riskScan.isError && <ErrorBlock error={riskScan.error} />}

      {contextualize.data && (
        <ResultBlock title="Explanation">
          <p className="whitespace-pre-wrap text-sm text-zinc-200">
            {contextualize.data.explanation}
          </p>
          {contextualize.data.citation_warning && (
            <p className="mt-2 text-xs font-medium text-amber-400">
              ⚠ The model referenced a citation it wasn&apos;t given.
            </p>
          )}
          {(contextualize.data.used_hints ?? []).length > 0 && (
            <ul className="mt-2 list-disc pl-5 text-xs text-zinc-400">
              {(contextualize.data.used_hints ?? []).map((hint, i) => (
                <li key={i}>{hint}</li>
              ))}
            </ul>
          )}
        </ResultBlock>
      )}
      {contextualize.isError && <ErrorBlock error={contextualize.error} />}
    </div>
  );
}

function ResultBlock({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-xl border border-white/10 bg-white/[0.04] p-3">
      <h4 className="mb-1 text-xs font-semibold uppercase tracking-wide text-zinc-500">
        {title}
      </h4>
      {children}
    </div>
  );
}

function ErrorBlock({ error }: { error: unknown }) {
  return (
    <p role="alert" className="text-sm text-red-400">
      Error: {error instanceof Error ? error.message : String(error)}
    </p>
  );
}

function RiskScanResult({
  data,
}: {
  data: import("@/lib/api").RiskScanResponse;
}) {
  const flags = (data.flagged_clauses ?? []).flatMap((fc) => [
    ...(fc.keyword_flags ?? []).map((f) => ({ term: f.term, note: f.predefined_explanation })),
    ...(fc.contextual_flags ?? []).map((f) => ({ term: f.term, note: f.explanation })),
  ]);
  return (
    <div>
      <p className="mb-2 text-sm text-zinc-300">{data.risk_summary}</p>
      {flags.length > 0 ? (
        <ul className="flex flex-col gap-1">
          {flags.map((f, i) => (
            <li key={i} className="rounded border border-amber-500/30 bg-amber-500/10 px-2 py-1 text-xs text-amber-300">
              <strong>{f.term}</strong> — {f.note}
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-xs text-zinc-500">No specific risk terms flagged.</p>
      )}
    </div>
  );
}
