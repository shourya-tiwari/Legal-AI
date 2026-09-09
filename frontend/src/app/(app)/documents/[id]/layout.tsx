"use client";

import { useParams } from "next/navigation";
import { WorkspaceProvider } from "@/components/workspace/workspace-context";
import { WorkspaceChrome } from "@/components/workspace/workspace-chrome";

export default function WorkspaceLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const params = useParams<{ id: string }>();
  const id = Number(params.id);

  return (
    <WorkspaceProvider id={id}>
      <WorkspaceChrome />
      <div className="mx-auto w-full max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
        {children}
      </div>
    </WorkspaceProvider>
  );
}
