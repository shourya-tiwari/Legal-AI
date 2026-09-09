"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { analyzeDocument, type AnalysisMode } from "@/lib/api";
import { qk } from "@/lib/query-keys";
import { useDocuments } from "@/lib/stores/documents";

/**
 * Shared agent-analysis runner. The Agents and Negotiation tabs both need the
 * `analyze()` result; this keeps one cached copy per (doc, mode, planner) and
 * exposes an imperative `run`.
 */
export function useAnalysis(
  id: number,
  mode: AnalysisMode = "full",
  useAiPlanner = false,
) {
  const qc = useQueryClient();
  const updateDoc = useDocuments((s) => s.update);
  const key = qk.analyze(id, mode, useAiPlanner);

  const mutation = useMutation({
    mutationFn: () =>
      analyzeDocument(id, { analysis_mode: mode, use_ai_planner: useAiPlanner }),
    onSuccess: (data) => {
      qc.setQueryData(key, data);
      updateDoc(id, {
        lastAnalyzedAt: new Date().toISOString(),
        needsReview: data.needs_human_review,
      });
    },
  });

  const cached = qc.getQueryData<Awaited<ReturnType<typeof analyzeDocument>>>(key);

  return {
    data: mutation.data ?? cached,
    isPending: mutation.isPending,
    isError: mutation.isError,
    error: mutation.error,
    run: mutation.mutate,
    hasRun: !!(mutation.data ?? cached),
  };
}
