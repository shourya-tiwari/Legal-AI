"use client";

import * as React from "react";
import dynamic from "next/dynamic";
import { useQuery, useMutation } from "@tanstack/react-query";
import { Network, Plus, RefreshCw } from "lucide-react";
import { toast } from "sonner";
import { getKgGraph, ingestKg } from "@/lib/api";
import { qk } from "@/lib/query-keys";
import { useWorkspace } from "@/components/workspace/workspace-context";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

const KgGraphCanvas = dynamic(
  () =>
    import("@/components/workspace/kg-graph-canvas").then(
      (m) => m.KgGraphCanvas,
    ),
  { ssr: false, loading: () => <Skeleton className="h-[560px] w-full" /> },
);

export default function GraphPage() {
  const { id } = useWorkspace();

  const graph = useQuery({
    queryKey: qk.kgGraph(id),
    queryFn: () => getKgGraph(id),
  });

  const ingest = useMutation({
    mutationFn: () => ingestKg(id),
    onSuccess: (r) => {
      if (r.kg_available) {
        toast.success(
          `Ingested — ${r.clauses} clauses, ${r.defined_terms} terms, ${r.portfolio_links_created} portfolio links`,
        );
        graph.refetch();
      } else {
        toast.warning("Knowledge graph is offline");
      }
    },
    onError: (e) => toast.error("Ingest failed", { description: String(e) }),
  });

  const data = graph.data;
  const nodes = (data?.nodes ?? []) as { id: string; label: string; type: string }[];
  const edges = (data?.edges ?? []) as {
    source: string;
    target: string;
    type: string;
  }[];
  const kgAvailable = data?.kg_available ?? true;
  const nodeTypeCounts = nodes.reduce<Record<string, number>>((acc, n) => {
    acc[n.type] = (acc[n.type] ?? 0) + 1;
    return acc;
  }, {});
  const portfolioLinks = edges.filter((e) => e.type === "SAME_AS").length;

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap gap-1.5">
          {Object.entries(nodeTypeCounts).map(([t, c]) => (
            <Badge key={t} variant="outline">
              {t}: {c}
            </Badge>
          ))}
          {portfolioLinks > 0 && (
            <Badge variant="danger">{portfolioLinks} portfolio links</Badge>
          )}
        </div>
        <div className="flex gap-2">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => ingest.mutate()}
            loading={ingest.isPending}
          >
            <Plus /> Ingest / refresh
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => graph.refetch()}
            disabled={graph.isFetching}
          >
            <RefreshCw />
          </Button>
        </div>
      </div>

      {!kgAvailable && (
        <Alert variant="warning">
          <Network />
          <div>
            <AlertTitle>Knowledge graph offline</AlertTitle>
            <AlertDescription>
              Memgraph / KùzuDB isn&rsquo;t reachable. The rest of the workspace
              is unaffected — KG features fail soft.
            </AlertDescription>
          </div>
        </Alert>
      )}

      {graph.isLoading ? (
        <Skeleton className="h-[560px] w-full" />
      ) : nodes.length === 0 ? (
        <EmptyState
          icon={Network}
          title="Nothing in the graph yet"
          description={
            kgAvailable
              ? "Ingest this document to populate its clause / defined-term / cross-reference graph."
              : "The knowledge graph service is offline."
          }
          action={
            kgAvailable && (
              <Button onClick={() => ingest.mutate()} loading={ingest.isPending}>
                <Plus /> Ingest this document
              </Button>
            )
          }
        />
      ) : (
        <>
          <KgGraphCanvas nodes={nodes} edges={edges} />
          <Card>
            <CardContent className="pt-5 text-xs text-muted-foreground">
              <p>
                <span className="inline-block size-2 rounded-full bg-danger align-middle" />{" "}
                Animated red edges are <code>SAME_AS</code> portfolio links —
                the same defined term recognised across documents. Node columns:
                Document → Defined Terms → Clauses → Cross-references.
              </p>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
