"use client";

import { useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { getDocument, getSensitivity } from "@/lib/api";
import { SiteHeader } from "@/components/SiteHeader";
import { SensitivityBadge } from "@/components/SensitivityBadge";
import { ClauseList, type Block } from "@/components/ClauseList";
import { ClauseActions } from "@/components/ClauseActions";
import { DocumentActions } from "@/components/DocumentActions";
import { AnalysisPanel } from "@/components/AnalysisPanel";

export default function DocumentPage() {
  const params = useParams<{ id: string }>();
  const documentId = Number(params.id);
  const [selectedBlockId, setSelectedBlockId] = useState<string | number | null>(null);

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["document", documentId],
    queryFn: () => getDocument(documentId),
    enabled: Number.isFinite(documentId),
  });

  const { data: sensitivity } = useQuery({
    queryKey: ["sensitivity", documentId],
    queryFn: () => getSensitivity(documentId),
    enabled: Number.isFinite(documentId),
  });

  if (isLoading) {
    return (
      <PageShell>
        <CenteredMessage>Loading document…</CenteredMessage>
      </PageShell>
    );
  }

  if (isError || !data) {
    return (
      <PageShell>
        <CenteredMessage>
          <p role="alert" className="text-red-700">
            Error loading document: {error instanceof Error ? error.message : "not found"}
          </p>
          <Link href="/" className="mt-3 inline-block text-sm text-blue-600 underline">
            Upload a new document
          </Link>
        </CenteredMessage>
      </PageShell>
    );
  }

  const blocks: Block[] = (data.blocks ?? []) as unknown as Block[];
  const selectedBlock = blocks.find((b) => String(b.id) === String(selectedBlockId)) ?? null;

  return (
    <PageShell>
      <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-6 px-6 py-8">
        <header className="flex flex-wrap items-center justify-between gap-3 border-b border-zinc-200 pb-4">
          <div>
            <Link href="/" className="text-xs text-zinc-500 hover:underline">
              ← Upload another document
            </Link>
            <h1 className="text-xl font-semibold text-zinc-900">{data.filename}</h1>
          </div>
          <SensitivityBadge
            tier={data.sensitivity_tier}
            externalProvidersPermitted={sensitivity?.external_providers_permitted ?? true}
          />
        </header>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,320px)_1fr]">
          <section aria-label="Extracted clauses" className="flex flex-col gap-2">
            <h2 className="text-sm font-semibold text-zinc-700">
              Clauses ({blocks.length})
            </h2>
            <ClauseList blocks={blocks} selectedId={selectedBlockId} onSelect={setSelectedBlockId} />
          </section>

          <section className="flex flex-col gap-6">
            {selectedBlock ? (
              <ClauseActions documentId={documentId} block={selectedBlock} />
            ) : (
              <p className="rounded-lg border border-dashed border-zinc-300 p-4 text-sm text-zinc-500">
                Select a clause on the left to rewrite, risk-scan, or contextualize it — or use the
                whole-document actions below.
              </p>
            )}

            <DocumentActions documentId={documentId} />
            <AnalysisPanel documentId={documentId} />
          </section>
        </div>
      </main>
    </PageShell>
  );
}

function PageShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex flex-1 flex-col">
      <SiteHeader />
      {children}
    </div>
  );
}

function CenteredMessage({ children }: { children: React.ReactNode }) {
  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-2 px-4 text-center text-sm text-zinc-600">
      {children}
    </main>
  );
}
