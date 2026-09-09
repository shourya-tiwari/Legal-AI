"use client";

import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { getDocument, getSensitivity, type DocumentQuality } from "@/lib/api";
import { qk } from "@/lib/query-keys";

export interface WorkspaceBlock {
  id: number | string;
  text: string;
  type?: string;
  page?: number;
}

interface WorkspaceValue {
  id: number;
  document: ReturnType<typeof useQuery<Awaited<ReturnType<typeof getDocument>>>>;
  sensitivity: ReturnType<
    typeof useQuery<Awaited<ReturnType<typeof getSensitivity>>>
  >;
  blocks: WorkspaceBlock[];
  quality: DocumentQuality | null;
}

const Ctx = React.createContext<WorkspaceValue | null>(null);

export function WorkspaceProvider({
  id,
  children,
}: {
  id: number;
  children: React.ReactNode;
}) {
  const document = useQuery({
    queryKey: qk.document(id),
    queryFn: () => getDocument(id),
    enabled: Number.isFinite(id),
    staleTime: 5 * 60_000,
  });
  const sensitivity = useQuery({
    queryKey: qk.sensitivity(id),
    queryFn: () => getSensitivity(id),
    enabled: Number.isFinite(id),
    staleTime: 5 * 60_000,
  });

  const value = React.useMemo<WorkspaceValue>(
    () => ({
      id,
      document,
      sensitivity,
      blocks: (document.data?.blocks ?? []) as unknown as WorkspaceBlock[],
      quality:
        (document.data?.quality as unknown as DocumentQuality | null) ?? null,
    }),
    [id, document, sensitivity],
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useWorkspace() {
  const v = React.useContext(Ctx);
  if (!v) throw new Error("useWorkspace must be used inside WorkspaceProvider");
  return v;
}
