"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

interface UIState {
  commandOpen: boolean;
  setCommandOpen: (open: boolean) => void;
  sidebarCollapsed: boolean;
  toggleSidebar: () => void;
  mobileNavOpen: boolean;
  setMobileNavOpen: (open: boolean) => void;
  /** documents list view preference */
  docsView: "grid" | "list";
  setDocsView: (v: "grid" | "list") => void;
}

export const useUI = create<UIState>()(
  persist(
    (set) => ({
      commandOpen: false,
      setCommandOpen: (open) => set({ commandOpen: open }),
      sidebarCollapsed: false,
      toggleSidebar: () =>
        set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
      mobileNavOpen: false,
      setMobileNavOpen: (open) => set({ mobileNavOpen: open }),
      docsView: "grid",
      setDocsView: (v) => set({ docsView: v }),
    }),
    {
      name: "legalai.ui",
      partialize: (s) => ({
        sidebarCollapsed: s.sidebarCollapsed,
        docsView: s.docsView,
      }),
    },
  ),
);
