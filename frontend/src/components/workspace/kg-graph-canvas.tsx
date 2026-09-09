"use client";

import * as React from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  type Node,
  type Edge,
  Handle,
  Position,
  MarkerType,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { cn } from "@/lib/utils";

type RawNode = { id: string; label: string; type: string };
type RawEdge = { source: string; target: string; type: string };

const TYPE_STYLE: Record<string, string> = {
  Document: "border-primary/50 bg-primary-muted text-primary",
  Clause: "border-border-strong bg-surface",
  DefinedTerm: "border-info/40 bg-info/10 text-info",
  CrossReferenceTarget: "border-warning/40 bg-warning/10 text-warning-foreground",
};

function KgNode({ data }: { data: { label: string; type: string; portfolio?: boolean } }) {
  return (
    <div
      className={cn(
        "max-w-[180px] rounded-lg border px-2.5 py-1.5 text-xs shadow-sm",
        TYPE_STYLE[data.type] ?? "border-border bg-surface",
        data.portfolio && "ring-2 ring-danger ring-offset-1 ring-offset-background",
      )}
    >
      <Handle type="target" position={Position.Left} className="!bg-border-strong" />
      <p className="line-clamp-2 font-medium">{data.label}</p>
      <p className="text-[10px] opacity-70">{data.type}</p>
      <Handle type="source" position={Position.Right} className="!bg-border-strong" />
    </div>
  );
}

const nodeTypes = { kg: KgNode };

/** Simple typed-column layout — good enough for a per-document graph. */
function layout(raw: RawNode[]): Node[] {
  const columns: Record<string, number> = {
    Document: 0,
    DefinedTerm: 1,
    Clause: 2,
    CrossReferenceTarget: 3,
  };
  const perColumn: Record<number, number> = {};
  return raw.map((n) => {
    const col = columns[n.type] ?? 2;
    const row = (perColumn[col] = (perColumn[col] ?? 0) + 1);
    return {
      id: n.id,
      type: "kg",
      position: { x: col * 280, y: row * 78 },
      data: { label: n.label, type: n.type },
    };
  });
}

export function KgGraphCanvas({
  nodes: rawNodes,
  edges: rawEdges,
}: {
  nodes: RawNode[];
  edges: RawEdge[];
}) {
  const nodes = React.useMemo(() => layout(rawNodes), [rawNodes]);
  const edges: Edge[] = React.useMemo(
    () =>
      rawEdges.map((e, i) => ({
        id: `e${i}`,
        source: e.source,
        target: e.target,
        label: e.type,
        labelStyle: { fontSize: 9, fill: "var(--color-subtle-foreground)" },
        style: {
          stroke:
            e.type === "SAME_AS"
              ? "var(--color-danger)"
              : "var(--color-border-strong)",
          strokeWidth: e.type === "SAME_AS" ? 2 : 1.5,
        },
        markerEnd: { type: MarkerType.ArrowClosed, width: 14, height: 14 },
        animated: e.type === "SAME_AS",
      })),
    [rawEdges],
  );

  return (
    <div className="h-[560px] w-full overflow-hidden rounded-xl border border-border bg-background">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
        proOptions={{ hideAttribution: true }}
        minZoom={0.2}
      >
        <Background color="var(--color-border)" gap={20} />
        <Controls className="!border-border !bg-surface [&_button]:!border-border [&_button]:!bg-surface [&_button]:!fill-foreground" />
        <MiniMap
          pannable
          zoomable
          className="!bg-surface"
          maskColor="color-mix(in oklch, var(--color-background) 70%, transparent)"
          nodeColor="var(--color-border-strong)"
        />
      </ReactFlow>
    </div>
  );
}
