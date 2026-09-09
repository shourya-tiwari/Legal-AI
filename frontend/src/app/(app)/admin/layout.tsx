"use client";

import { ADMIN_TABS } from "@/components/layout/nav-config";
import { PageHeader } from "@/components/layout/page-header";
import { RouteTabs } from "@/components/layout/route-tabs";

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <>
      <PageHeader
        title="Administration"
        description="Users, routing policy overrides, the Class-C egress log, feature flags, and backend health. Write actions require an admin role."
      >
        <RouteTabs tabs={ADMIN_TABS} />
      </PageHeader>
      <div className="mx-auto w-full max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
        {children}
      </div>
    </>
  );
}
