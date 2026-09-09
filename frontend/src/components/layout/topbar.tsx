"use client";

import { Menu, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Kbd } from "@/components/ui/kbd";
import { Sheet, SheetContent, SheetTrigger, SheetTitle } from "@/components/ui/sheet";
import { useUI } from "@/lib/stores/ui";
import { ThemeToggle } from "./theme-toggle";
import { UserMenu } from "./user-menu";
import { SidebarNav } from "./sidebar-nav";

export function Topbar() {
  const setCommandOpen = useUI((s) => s.setCommandOpen);
  const mobileOpen = useUI((s) => s.mobileNavOpen);
  const setMobileOpen = useUI((s) => s.setMobileNavOpen);

  return (
    <header className="sticky top-0 z-30 flex h-14 items-center gap-3 border-b border-border bg-background/80 px-4 backdrop-blur-md">
      <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
        <SheetTrigger asChild>
          <Button variant="ghost" size="icon" className="lg:hidden" aria-label="Open navigation">
            <Menu />
          </Button>
        </SheetTrigger>
        <SheetContent side="left" className="w-72 p-0">
          <SheetTitle className="sr-only">Navigation</SheetTitle>
          <SidebarNav onNavigate={() => setMobileOpen(false)} />
        </SheetContent>
      </Sheet>

      <button
        onClick={() => setCommandOpen(true)}
        className="group flex h-9 w-full max-w-sm items-center gap-2 rounded-lg border border-border bg-surface px-3 text-sm text-subtle-foreground transition-colors hover:border-border-strong hover:text-muted-foreground"
      >
        <Search className="size-4" />
        <span>Search…</span>
        <span className="ml-auto flex items-center gap-0.5">
          <Kbd>⌘</Kbd>
          <Kbd>K</Kbd>
        </span>
      </button>

      <div className="ml-auto flex items-center gap-1">
        <ThemeToggle />
        <UserMenu />
      </div>
    </header>
  );
}
