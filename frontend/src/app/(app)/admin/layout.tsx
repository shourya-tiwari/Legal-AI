"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ADMIN_TABS } from "@/components/layout/nav-config";
import { isActive } from "@/components/layout/sidebar-nav";
import { PageHeader } from "@/components/layout/page-header";
import { cn } from "@/lib/utils";

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();

  return (
    <>
      <PageHeader
        title="Administration"
        description="Users, routing policy overrides, the Class-C egress log, feature flags, and backend health. Write actions require an admin role."
      >
        <div className="-mb-px mt-4 flex gap-1 overflow-x-auto">
          {ADMIN_TABS.map((tab) => {
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
                    : "border-transparent text-muted-foreground hover:text-foreground",
                )}
              >
                <tab.icon className="size-4" />
                {tab.label}
              </Link>
            );
          })}
        </div>
      </PageHeader>
      <div className="mx-auto w-full max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
        {children}
      </div>
    </>
  );
}
