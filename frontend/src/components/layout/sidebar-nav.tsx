"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { PanelLeftClose, PanelLeft, ArrowUpRight } from "lucide-react";
import {
  APP_NAV,
  RESOURCES_NAV,
  SETTINGS_NAV_ITEM,
  WEBSITE_NAV_ITEM,
  GITHUB_URL,
  filterReadyNav,
  type NavItem,
} from "./nav-config";
import { Logo } from "./logo";
import { GithubIcon } from "@/components/shared/brand-icons";
import { useUI } from "@/lib/stores/ui";
import { cn } from "@/lib/utils";
import { Tooltip } from "@/components/ui/tooltip";

export function isActive(pathname: string, href: string, exact?: boolean) {
  if (exact) return pathname === href;
  return pathname === href || pathname.startsWith(href + "/");
}

function itemActive(pathname: string, item: NavItem) {
  if (item.match) return item.match(pathname);
  return isActive(pathname, item.href, item.exact);
}

export function SidebarNav({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  const collapsed = useUI((s) => s.sidebarCollapsed);
  const toggle = useUI((s) => s.toggleSidebar);

  function row(item: NavItem, active: boolean) {
    const link = (
      <Link
        href={item.href}
        onClick={onNavigate}
        aria-current={active ? "page" : undefined}
        className={cn(
          "group flex items-center gap-2.5 rounded-lg px-2 py-2 text-sm font-medium transition-colors",
          collapsed && "justify-center px-0",
          active
            ? "bg-primary-muted text-primary"
            : "text-muted-foreground hover:bg-muted hover:text-foreground",
        )}
      >
        <item.icon
          className={cn(
            "size-4 shrink-0",
            active
              ? "text-primary"
              : "text-subtle-foreground group-hover:text-foreground",
          )}
        />
        {!collapsed && <span className="truncate">{item.label}</span>}
        {!collapsed && item.external && (
          <ArrowUpRight className="ml-auto size-3.5 shrink-0 text-subtle-foreground opacity-0 transition-opacity group-hover:opacity-100" />
        )}
      </Link>
    );
    return (
      <li key={item.href}>
        {collapsed ? (
          <Tooltip content={item.label} side="right">
            {link}
          </Tooltip>
        ) : (
          link
        )}
      </li>
    );
  }

  return (
    <div className="flex h-full flex-col">
      <div
        className={cn(
          "flex h-14 items-center border-b border-border px-3",
          collapsed ? "justify-center" : "justify-between",
        )}
      >
        <Logo showWordmark={!collapsed} href="/dashboard" />
        {!collapsed && (
          <button
            onClick={toggle}
            className="hidden rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground lg:block"
            aria-label="Collapse sidebar"
          >
            <PanelLeftClose className="size-4" />
          </button>
        )}
      </div>

      <nav
        className="flex-1 space-y-6 overflow-y-auto px-3 py-4"
        aria-label="Primary"
      >
        {filterReadyNav(APP_NAV).map((group) => (
          <div key={group.label}>
            {!collapsed && (
              <p className="px-2 pb-1.5 text-[11px] font-medium uppercase tracking-wider text-subtle-foreground">
                {group.label}
              </p>
            )}
            <ul className="space-y-0.5">
              {group.items.map((item) =>
                row(item, itemActive(pathname, item)),
              )}
            </ul>
          </div>
        ))}

        <div>
          {!collapsed && (
            <p className="px-2 pb-1.5 text-[11px] font-medium uppercase tracking-wider text-subtle-foreground">
              Resources
            </p>
          )}
          <ul className="space-y-0.5">
            {RESOURCES_NAV.map((item) => row(item, false))}
          </ul>
        </div>
      </nav>

      <div className="space-y-0.5 border-t border-border p-3">
        {collapsed ? (
          <button
            onClick={toggle}
            className="mx-auto flex rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
            aria-label="Expand sidebar"
          >
            <PanelLeft className="size-4" />
          </button>
        ) : (
          <>
            <ul className="space-y-0.5">
              {row(
                SETTINGS_NAV_ITEM,
                itemActive(pathname, SETTINGS_NAV_ITEM),
              )}
              {row(WEBSITE_NAV_ITEM, false)}
            </ul>
            <a
              href={GITHUB_URL}
              target="_blank"
              rel="noreferrer"
              className="group flex items-center gap-2.5 rounded-lg px-2 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
            >
              <GithubIcon className="size-4 shrink-0 text-subtle-foreground group-hover:text-foreground" />
              <span className="truncate">GitHub</span>
              <ArrowUpRight className="ml-auto size-3.5 shrink-0 text-subtle-foreground opacity-0 transition-opacity group-hover:opacity-100" />
            </a>
          </>
        )}
      </div>
    </div>
  );
}
