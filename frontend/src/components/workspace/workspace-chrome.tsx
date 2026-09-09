"use client";

import { useRouter } from "next/navigation";
import { Download, AlertTriangle, Trash2, MoreHorizontal } from "lucide-react";
import { toast } from "sonner";
import { useMutation } from "@tanstack/react-query";
import { originalFileUrl, ingestKg } from "@/lib/api";
import { useDocuments } from "@/lib/stores/documents";
import { WORKSPACE_TABS } from "@/components/layout/nav-config";
import { PageHeader } from "@/components/layout/page-header";
import { RouteTabs } from "@/components/layout/route-tabs";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { SensitivityBadge } from "@/components/shared/sensitivity-badge";
import { SensitivityOverrideDialog } from "@/components/workspace/sensitivity-override";
import { VersionHistoryDialog } from "@/components/workspace/version-history";
import { useWorkspace } from "./workspace-context";
import { bytes, relativeTime } from "@/lib/format";

export function WorkspaceChrome() {
  const router = useRouter();
  const { id, document, sensitivity, blocks, quality } = useWorkspace();
  const removeFromLibrary = useDocuments((s) => s.remove);

  const ingest = useMutation({
    mutationFn: () => ingestKg(id),
    onSuccess: (r) =>
      toast[r.kg_available ? "success" : "warning"](
        r.kg_available
          ? `Ingested — ${r.clauses} clauses, ${r.defined_terms} defined terms`
          : "Knowledge graph is offline — nothing written",
      ),
    onError: (e) => toast.error("Ingest failed", { description: String(e) }),
  });

  const d = document.data;
  const tabs = WORKSPACE_TABS(id);

  return (
    <>
      <PageHeader
        title={
          document.isLoading ? (
            <Skeleton className="h-7 w-72" />
          ) : (
            (d?.filename ?? "Document")
          )
        }
        breadcrumbs={[
          { label: "Documents", href: "/documents" },
          { label: d?.filename ?? "…" },
        ]}
        description={
          d && (
            <span className="flex flex-wrap items-center gap-x-2 gap-y-0.5">
              <span>{blocks.length} clauses</span>
              <span>·</span>
              <span>{d.content_type ?? "unknown type"}</span>
              {d.created_at && (
                <>
                  <span>·</span>
                  <span>uploaded {relativeTime(d.created_at)}</span>
                </>
              )}
            </span>
          )
        }
        actions={
          d && (
            <>
              <SensitivityBadge
                tier={d.sensitivity_tier}
                externalAllowed={sensitivity.data?.external_providers_permitted}
              />
              {d.original_available && (
                <Button variant="secondary" size="sm" asChild>
                  <a href={originalFileUrl(id)}>
                    <Download /> Original
                    <span className="hidden sm:inline">
                      {" "}
                      ({bytes(d.original_size)})
                    </span>
                  </a>
                </Button>
              )}
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" size="icon" aria-label="Document actions">
                    <MoreHorizontal />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <SensitivityOverrideDialog
                    documentId={id}
                    current={d.sensitivity_tier}
                  />
                  <DropdownMenuItem
                    onSelect={(e) => {
                      e.preventDefault();
                      ingest.mutate();
                    }}
                  >
                    Add to knowledge graph
                  </DropdownMenuItem>
                  <VersionHistoryDialog documentId={id} />
                  <DropdownMenuItem
                    variant="danger"
                    onClick={() => {
                      removeFromLibrary(id);
                      toast.success("Removed from library");
                      router.push("/documents");
                    }}
                  >
                    <Trash2 /> Remove from library
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </>
          )
        }
      >
        <RouteTabs tabs={tabs} />
      </PageHeader>

      {quality && quality.low_quality_pages.length > 0 && (
        <div className="mx-auto w-full max-w-7xl px-4 pt-6 sm:px-6 lg:px-8">
          <Alert variant="warning">
            <AlertTriangle />
            <div>
              <AlertTitle>Scan quality warning</AlertTitle>
              <AlertDescription>
                {quality.low_quality_pages.length} of {quality.pages_assessed}{" "}
                page(s) flagged low-quality (pages{" "}
                {quality.low_quality_pages.join(", ")}). OCR may be less reliable
                there.
                {(quality.pages_with_redactions?.length ?? 0) > 0 &&
                  ` Redaction boxes on page(s) ${quality.pages_with_redactions!.join(
                    ", ",
                  )}.`}
              </AlertDescription>
            </div>
          </Alert>
        </div>
      )}
      {document.isError && (
        <div className="mx-auto w-full max-w-7xl px-4 pt-6 sm:px-6 lg:px-8">
          <Alert variant="danger">
            <AlertTriangle />
            <AlertDescription>
              Could not load this document. It may have been removed, or the
              backend is unreachable.
            </AlertDescription>
          </Alert>
        </div>
      )}
    </>
  );
}
