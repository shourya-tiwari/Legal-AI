"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { askDocument, mapDocument, rewriteDocument, riskScanDocument } from "@/lib/api";

export function DocumentActions({ documentId }: { documentId: number }) {
  const [question, setQuestion] = useState("");

  const rewrite = useMutation({ mutationFn: () => rewriteDocument(documentId, null) });
  const map = useMutation({ mutationFn: () => mapDocument(documentId) });
  const riskScan = useMutation({ mutationFn: () => riskScanDocument(documentId, null) });
  const ask = useMutation({ mutationFn: (q: string) => askDocument(documentId, q) });

  return (
    <div className="flex flex-col gap-4 rounded-2xl border border-white/10 bg-white/[0.04] p-5 shadow-sm backdrop-blur">
      <h2 className="text-sm font-semibold text-zinc-300">Whole-document actions</h2>

      <div className="flex flex-wrap gap-2">
        <ActionButton label="Rewrite whole document" pending={rewrite.isPending} pendingLabel="Rewriting…" onClick={() => rewrite.mutate()} />
        <ActionButton label="Extract timeline" pending={map.isPending} pendingLabel="Extracting…" onClick={() => map.mutate()} />
        <ActionButton label="Scan for risk" pending={riskScan.isPending} pendingLabel="Scanning…" onClick={() => riskScan.mutate()} />
      </div>

      <form
        className="flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          if (question.trim()) ask.mutate(question.trim());
        }}
      >
        <input
          className="flex-1 rounded-full border border-zinc-700 bg-zinc-900 px-3.5 py-1.5 text-sm text-zinc-100 placeholder:text-zinc-500 focus:border-indigo-400/50 focus:outline-none"
          placeholder="Ask a question about this contract…"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
        />
        <button
          type="submit"
          disabled={ask.isPending || !question.trim()}
          className="rounded-full bg-gradient-to-r from-indigo-500 to-blue-500 px-4 py-1.5 text-sm font-semibold text-white shadow-sm shadow-indigo-950 transition-transform hover:scale-[1.03] disabled:opacity-50 disabled:from-zinc-700 disabled:to-zinc-700 disabled:shadow-none"
        >
          {ask.isPending ? "Asking…" : "Ask"}
        </button>
      </form>

      {rewrite.data && (
        <Result title="Plain-English rewrite">
          <p className="max-h-64 overflow-y-auto whitespace-pre-wrap text-sm text-zinc-200">
            {rewrite.data.rewritten_text}
          </p>
        </Result>
      )}
      {rewrite.isError && <Err error={rewrite.error} />}

      {map.data && (
        <Result title="Timeline">
          {map.data.timeline.length > 0 ? (
            <ul className="flex flex-col gap-1">
              {map.data.timeline.map((ev, i) => (
                <li key={i} className="text-sm text-zinc-200">
                  <strong>{ev.date_description}:</strong> {ev.event}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-xs text-zinc-500">No dated events extracted.</p>
          )}
        </Result>
      )}
      {map.isError && <Err error={map.error} />}

      {riskScan.data && (
        <Result title="Risk scan">
          <p className="text-sm text-zinc-300">{riskScan.data.risk_summary}</p>
        </Result>
      )}
      {riskScan.isError && <Err error={riskScan.error} />}

      {ask.data && (
        <Result title="Answer">
          <p className="whitespace-pre-wrap text-sm text-zinc-200">{ask.data.answer}</p>
        </Result>
      )}
      {ask.isError && <Err error={ask.error} />}
    </div>
  );
}

function ActionButton({
  label,
  pendingLabel,
  pending,
  onClick,
}: {
  label: string;
  pendingLabel: string;
  pending: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={pending}
      className="rounded-full border border-zinc-700 bg-zinc-900 px-3.5 py-1.5 text-sm font-medium text-zinc-300 transition-colors hover:border-indigo-400/50 hover:bg-indigo-500/10 hover:text-indigo-300 disabled:opacity-50"
    >
      {pending ? pendingLabel : label}
    </button>
  );
}

function Result({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-white/10 bg-white/[0.04] p-3">
      <h4 className="mb-1 text-xs font-semibold uppercase tracking-wide text-zinc-500">{title}</h4>
      {children}
    </div>
  );
}

function Err({ error }: { error: unknown }) {
  return (
    <p role="alert" className="text-sm text-red-400">
      Error: {error instanceof Error ? error.message : String(error)}
    </p>
  );
}
