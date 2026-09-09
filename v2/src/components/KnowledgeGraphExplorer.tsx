"use client";

import { useEffect, useRef, useState } from "react";
import cytoscape, { type Core, type ElementDefinition } from "cytoscape";
import { useMutation } from "@tanstack/react-query";
import { getKgGraph, type KGGraphResponse } from "@/lib/api";

// docs/v2/ROADMAP.md Phase 8 / docs/v2/FRONTEND.md: "Knowledge Graph
// Explorer's visual graph (Cytoscape.js) -- not built yet". The existing
// KnowledgeGraphPanel is text-only (JSON.stringify'd query results); this
// renders the actual node/edge shape from GET /api/kg/documents/{id}/graph
// as a real graph, using Cytoscape.js directly (not react-cytoscapejs --
// one fewer dependency, and the imperative API is a natural fit for a
// ref-managed canvas that TanStack Query re-populates on refetch).

interface GraphNode {
  id: string;
  label: string;
  type: string;
  clause_type?: string;
  portfolio_linked?: boolean;
}

interface GraphEdge {
  source: string;
  target: string;
  type: string;
}

const NODE_COLORS: Record<string, string> = {
  Document: "#818cf8", // indigo-400
  Clause: "#71717a", // zinc-500
  DefinedTerm: "#34d399", // emerald-400
  CrossReferenceTarget: "#fbbf24", // amber-400
};

function toElements(nodes: GraphNode[], edges: GraphEdge[]): ElementDefinition[] {
  const nodeEls: ElementDefinition[] = nodes.map((n) => ({
    data: { id: n.id, label: n.label, type: n.type, portfolioLinked: n.portfolio_linked ?? false },
  }));
  const edgeEls: ElementDefinition[] = edges.map((e, i) => ({
    data: { id: `e${i}`, source: e.source, target: e.target, type: e.type },
  }));
  return [...nodeEls, ...edgeEls];
}

export function KnowledgeGraphExplorer({ documentId }: { documentId: number }) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const cyRef = useRef<Core | null>(null);
  const [selected, setSelected] = useState<GraphNode | null>(null);

  const graphQuery = useMutation({
    mutationFn: () => getKgGraph(documentId),
  });

  useEffect(() => {
    const data = graphQuery.data as KGGraphResponse | undefined;
    if (!data || !containerRef.current) return;

    const nodes = (data.nodes ?? []) as unknown as GraphNode[];
    const edges = (data.edges ?? []) as unknown as GraphEdge[];

    cyRef.current?.destroy();
    const cy = cytoscape({
      container: containerRef.current,
      elements: toElements(nodes, edges),
      style: [
        {
          selector: "node",
          style: {
            "background-color": (ele) => NODE_COLORS[ele.data("type")] ?? "#a1a1aa",
            "border-width": (ele) => (ele.data("portfolioLinked") ? 2 : 0),
            "border-color": "#f87171",
            label: "data(label)",
            "font-size": "8px",
            color: "#e4e4e7",
            "text-valign": "bottom",
            "text-margin-y": 4,
            width: 22,
            height: 22,
          },
        },
        {
          selector: "edge",
          style: {
            width: 1.5,
            "line-color": "#52525b",
            "target-arrow-color": "#52525b",
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
            "font-size": "6px",
            color: "#a1a1aa",
            label: "data(type)",
          },
        },
      ],
      layout: { name: "cose", animate: false, padding: 20 },
    });

    cy.on("tap", "node", (evt) => {
      const d = evt.target.data();
      const match = nodes.find((n) => n.id === d.id);
      setSelected(match ?? null);
    });

    cyRef.current = cy;
    return () => cy.destroy();
  }, [graphQuery.data]);

  const data = graphQuery.data;

  return (
    <div className="flex flex-col gap-4 rounded-2xl border border-white/10 bg-white/[0.04] p-5 shadow-sm backdrop-blur">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-zinc-300">Knowledge graph explorer</h2>
          <p className="text-xs text-zinc-500">
            Visual graph of this document&apos;s clauses, defined terms, cross-references, and any
            portfolio-linked terms (red border) from other documents.
          </p>
        </div>
        <button
          type="button"
          onClick={() => graphQuery.mutate()}
          disabled={graphQuery.isPending}
          className="rounded-full bg-zinc-900 px-4 py-1.5 text-sm font-semibold text-white transition-colors hover:bg-zinc-800 disabled:opacity-50"
        >
          {graphQuery.isPending ? "Loading…" : "Load graph"}
        </button>
      </div>

      {graphQuery.isError && (
        <p role="alert" className="text-sm text-red-400">
          Error: {graphQuery.error instanceof Error ? graphQuery.error.message : String(graphQuery.error)}
        </p>
      )}

      {data && !data.kg_available && (
        <p className="text-xs text-amber-300">Memgraph unreachable — graph is empty (fail-soft).</p>
      )}

      {data && data.kg_available && (data.nodes ?? []).length === 0 && (
        <p className="text-xs text-zinc-500">
          Nothing in the graph yet for this document — ingest it first (Knowledge graph panel above).
        </p>
      )}

      {data && (data.nodes ?? []).length > 0 && (
        <div className="flex flex-col gap-3 md:flex-row">
          <div
            ref={containerRef}
            className="h-80 flex-1 rounded-xl border border-white/10 bg-black/20"
          />
          <div className="w-full shrink-0 rounded-xl border border-white/10 bg-white/[0.02] p-3 text-xs md:w-56">
            <h4 className="mb-2 font-semibold uppercase tracking-wide text-zinc-500">
              {selected ? "Selected node" : "Click a node"}
            </h4>
            {selected ? (
              <div className="flex flex-col gap-1">
                <span
                  className="w-fit rounded-full px-2 py-0.5 font-medium text-black"
                  style={{ backgroundColor: NODE_COLORS[selected.type] ?? "#a1a1aa" }}
                >
                  {selected.type}
                </span>
                <p className="mt-1 text-zinc-300">{selected.label}</p>
                {selected.portfolio_linked && (
                  <p className="text-red-300">Linked from another document (SAME_AS)</p>
                )}
              </div>
            ) : (
              <p className="text-zinc-500">Node details appear here.</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
