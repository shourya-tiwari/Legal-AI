"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { isActive } from "./sidebar-nav";
import type { NavItem } from "./nav-config";
import { cn } from "@/lib/utils";

/**
 * The underline tab bar used for route-level sub-navigation (the document
 * workspace, the admin section). One implementation so the two never drift.
 * Render it inside a `PageHeader` — the negative bottom margin pulls the
 * active underline flush with the header's bottom border.
 */
export function RouteTabs({ tabs }: { tabs: NavItem[] }) {
  const pathname = usePathname();

  return (
    <div className="-mb-px mt-4 flex gap-1 overflow-x-auto">
      {tabs.map((tab) => {
        const active = isActive(pathname, tab.href, tab.exact);
        return (
          <Link
            key={tab.href}
            href={tab.href}
            aria-current={active ? "page" : undefined}
            className={cn(
              "flex shrink-0 items-center gap-1.5 border-b-2 px-3 py-2 text-sm font-medium transition-colors",
              active
                ? "border-primary text-foreground"
                : "border-transparent text-muted-foreground hover:border-border-strong hover:text-foreground",
            )}
          >
            <tab.icon className="size-4" />
            {tab.label}
          </Link>
        );
      })}
    </div>
  );
}
