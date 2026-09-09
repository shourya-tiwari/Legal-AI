"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import {
  ArrowRight,
  FileText,
  Moon,
  Sun,
  Monitor,
  Upload,
  Sparkles,
} from "lucide-react";
import { useTheme } from "next-themes";
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
  CommandShortcut,
} from "@/components/ui/command";
import {
  APP_NAV,
  MARKETING_NAV,
  RESOURCES_NAV,
  READY_ROUTES,
  SETTINGS_NAV_ITEM,
  WEBSITE_NAV_ITEM,
} from "./nav-config";
import { useUI } from "@/lib/stores/ui";
import { useDocuments } from "@/lib/stores/documents";
import { SENSITIVITY_META } from "@/lib/format";

export function CommandPalette() {
  const open = useUI((s) => s.commandOpen);
  const setOpen = useUI((s) => s.setCommandOpen);
  const router = useRouter();
  const { setTheme } = useTheme();
  const docs = useDocuments((s) => s.docs);

  React.useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen(!open);
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, setOpen]);

  const go = React.useCallback(
    (href: string) => {
      setOpen(false);
      router.push(href);
    },
    [router, setOpen],
  );

  const run = React.useCallback(
    (fn: () => void) => {
      setOpen(false);
      fn();
    },
    [setOpen],
  );

  return (
    <CommandDialog open={open} onOpenChange={setOpen}>
      <CommandInput placeholder="Search or jump to…" />
      <CommandList>
        <CommandEmpty>No results.</CommandEmpty>

        <CommandGroup heading="Quick actions">
          <CommandItem onSelect={() => go("/documents/upload")}>
            <Upload /> Upload a document
            <CommandShortcut>⌘U</CommandShortcut>
          </CommandItem>
          <CommandItem onSelect={() => go("/assistant")}>
            <Sparkles /> Open the AI Assistant
          </CommandItem>
        </CommandGroup>

        {docs.length > 0 && (
          <>
            <CommandSeparator />
            <CommandGroup heading="Recent documents">
              {docs.slice(0, 6).map((d) => (
                <CommandItem
                  key={d.id}
                  value={`doc ${d.filename} ${d.tags.join(" ")}`}
                  onSelect={() => go(`/documents/${d.id}`)}
                >
                  <FileText />
                  <span className="truncate">{d.filename}</span>
                  <span className="ml-auto text-[11px] text-subtle-foreground">
                    {SENSITIVITY_META[d.sensitivityTier]?.label ?? d.sensitivityTier}
                  </span>
                </CommandItem>
              ))}
            </CommandGroup>
          </>
        )}

        <CommandSeparator />
        <CommandGroup heading="Navigate">
          {[...APP_NAV.flatMap((g) => g.items), SETTINGS_NAV_ITEM]
            .filter((i) => READY_ROUTES.has(i.href))
            .map((item) => (
            <CommandItem
              key={item.href}
              value={`nav ${item.label} ${item.description ?? ""}`}
              onSelect={() => go(item.href)}
            >
                <item.icon />
                {item.label}
                <ArrowRight className="ml-auto opacity-0 group-data-[selected=true]:opacity-60" />
              </CommandItem>
            ))}
        </CommandGroup>

        <CommandSeparator />
        <CommandGroup heading="Resources">
          {[WEBSITE_NAV_ITEM, ...RESOURCES_NAV].map((item) => (
            <CommandItem
              key={item.href}
              value={`resource ${item.label}`}
              onSelect={() => go(item.href)}
            >
              <item.icon />
              {item.label}
            </CommandItem>
          ))}
        </CommandGroup>

        <CommandSeparator />
        <CommandGroup heading="Marketing">
          {MARKETING_NAV.map((item) => (
            <CommandItem
              key={item.href}
              value={`page ${item.label}`}
              onSelect={() => go(item.href)}
            >
              <item.icon />
              {item.label}
            </CommandItem>
          ))}
        </CommandGroup>

        <CommandSeparator />
        <CommandGroup heading="Theme">
          <CommandItem onSelect={() => run(() => setTheme("light"))}>
            <Sun /> Light
          </CommandItem>
          <CommandItem onSelect={() => run(() => setTheme("dark"))}>
            <Moon /> Dark
          </CommandItem>
          <CommandItem onSelect={() => run(() => setTheme("system"))}>
            <Monitor /> System
          </CommandItem>
        </CommandGroup>
      </CommandList>
    </CommandDialog>
  );
}
