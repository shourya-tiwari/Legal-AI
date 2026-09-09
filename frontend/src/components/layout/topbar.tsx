"use client";

import Link from "next/link";
import { Menu, Search, LifeBuoy, ArrowUpRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Kbd } from "@/components/ui/kbd";
import { Sheet, SheetContent, SheetTrigger, SheetTitle } from "@/components/ui/sheet";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { GithubIcon } from "@/components/shared/brand-icons";
import { useUI } from "@/lib/stores/ui";
import { RESOURCES_NAV, WEBSITE_NAV_ITEM, GITHUB_URL } from "./nav-config";
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
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              size="sm"
              className="hidden gap-1.5 text-muted-foreground sm:inline-flex"
            >
              <LifeBuoy className="size-4" />
              Resources
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            <DropdownMenuLabel>Website &amp; docs</DropdownMenuLabel>
            <DropdownMenuItem asChild>
              <Link href={WEBSITE_NAV_ITEM.href}>
                <WEBSITE_NAV_ITEM.icon /> Marketing site
              </Link>
            </DropdownMenuItem>
            {RESOURCES_NAV.map((item) => (
              <DropdownMenuItem key={item.href} asChild>
                <Link href={item.href}>
                  <item.icon /> {item.label}
                </Link>
              </DropdownMenuItem>
            ))}
            <DropdownMenuSeparator />
            <DropdownMenuItem asChild>
              <a href={GITHUB_URL} target="_blank" rel="noreferrer">
                <GithubIcon className="size-4" /> GitHub
                <ArrowUpRight className="ml-auto size-3.5 opacity-60" />
              </a>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
        <ThemeToggle />
        <UserMenu />
      </div>
    </header>
  );
}
