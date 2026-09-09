"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

/**
 * Client-side document library.
 *
 * The backend has no `GET /documents` list endpoint (documented gap in
 * docs/v2/FRONTEND_PLAN.md), so the library is whatever *this browser* has
 * uploaded. Each entry is hydrated on demand via `GET /v2/documents/{id}`.
 */
export interface LibraryDoc {
  id: number;
  filename: string;
  contentType: string | null;
  uploadedAt: string;
  sensitivityTier: string;
  clauseCount: number;
  tags: string[];
  /** last time a full agent analysis was run, for the dashboard */
  lastAnalyzedAt?: string;
  needsReview?: boolean;
}

interface DocumentsState {
  docs: LibraryDoc[];
  add: (doc: Omit<LibraryDoc, "tags">) => void;
  remove: (id: number) => void;
  update: (id: number, patch: Partial<LibraryDoc>) => void;
  addTag: (id: number, tag: string) => void;
  removeTag: (id: number, tag: string) => void;
  clear: () => void;
}

export const useDocuments = create<DocumentsState>()(
  persist(
    (set) => ({
      docs: [],
      add: (doc) =>
        set((s) => {
          const existing = s.docs.find((d) => d.id === doc.id);
          if (existing)
            return {
              docs: s.docs.map((d) =>
                d.id === doc.id ? { ...d, ...doc } : d,
              ),
            };
          return { docs: [{ ...doc, tags: [] }, ...s.docs] };
        }),
      remove: (id) => set((s) => ({ docs: s.docs.filter((d) => d.id !== id) })),
      update: (id, patch) =>
        set((s) => ({
          docs: s.docs.map((d) => (d.id === id ? { ...d, ...patch } : d)),
        })),
      addTag: (id, tag) =>
        set((s) => ({
          docs: s.docs.map((d) =>
            d.id === id && !d.tags.includes(tag)
              ? { ...d, tags: [...d.tags, tag] }
              : d,
          ),
        })),
      removeTag: (id, tag) =>
        set((s) => ({
          docs: s.docs.map((d) =>
            d.id === id ? { ...d, tags: d.tags.filter((t) => t !== tag) } : d,
          ),
        })),
      clear: () => set({ docs: [] }),
    }),
    { name: "legalai.documents" },
  ),
);

/** All tags across the library, sorted, unique. */
export function allTags(docs: LibraryDoc[]): string[] {
  return [...new Set(docs.flatMap((d) => d.tags))].sort();
}
