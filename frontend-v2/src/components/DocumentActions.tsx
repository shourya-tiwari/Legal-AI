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
    <div className="flex flex-col gap-4 rounded-lg border border-zinc-200 bg-white p-4">
      <h2 className="text-sm font-semibold text-zinc-700">Whole-document actions</h2>

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
          className="flex-1 rounded-md border border-zinc-300 px-3 py-1.5 text-sm"
          placeholder="Ask a question about this contract…"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
        />
        <button
          type="submit"
          disabled={ask.isPending || !question.trim()}
          className="rounded-md bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {ask.isPending ? "Asking…" : "Ask"}
        </button>
      </form>

      {rewrite.data && (
        <Result title="Plain-English rewrite">
          <p className="max-h-64 overflow-y-auto whitespace-pre-wrap text-sm text-zinc-800">
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
                <li key={i} className="text-sm text-zinc-800">
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
          <p className="text-sm text-zinc-700">{riskScan.data.risk_summary}</p>
        </Result>
      )}
      {riskScan.isError && <Err error={riskScan.error} />}

      {ask.data && (
        <Result title="Answer">
          <p className="whitespace-pre-wrap text-sm text-zinc-800">{ask.data.answer}</p>
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
      className="rounded-md border border-zinc-300 bg-white px-3 py-1.5 text-sm font-medium text-zinc-700 hover:bg-zinc-100 disabled:opacity-50"
    >
      {pending ? pendingLabel : label}
    </button>
  );
}

function Result({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-md border border-zinc-100 bg-zinc-50 p-3">
      <h4 className="mb-1 text-xs font-semibold uppercase tracking-wide text-zinc-500">{title}</h4>
      {children}
    </div>
  );
}

function Err({ error }: { error: unknown }) {
  return (
    <p role="alert" className="text-sm text-red-700">
      Error: {error instanceof Error ? error.message : String(error)}
    </p>
  );
}
