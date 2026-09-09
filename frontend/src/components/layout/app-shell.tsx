"use client";

import { useUI } from "@/lib/stores/ui";
import { cn } from "@/lib/utils";
import { SidebarNav } from "./sidebar-nav";
import { Topbar } from "./topbar";
import { CommandPalette } from "./command-palette";

export function AppShell({ children }: { children: React.ReactNode }) {
  const collapsed = useUI((s) => s.sidebarCollapsed);

  return (
    <div className="flex min-h-dvh">
      <aside
        className={cn(
          "sticky top-0 hidden h-dvh shrink-0 border-r border-border bg-surface lg:block",
          collapsed ? "w-16" : "w-64",
        )}
      >
        <SidebarNav />
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar />
        <main className="flex-1">{children}</main>
      </div>

      <CommandPalette />
    </div>
  );
}
