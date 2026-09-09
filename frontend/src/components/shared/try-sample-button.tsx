"use client";

import { useRouter } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { toast } from "sonner";
import { FlaskConical } from "lucide-react";
import { uploadDocument, type UploadResult } from "@/lib/api";
import { useDocuments } from "@/lib/stores/documents";
import { SAMPLE_CONTRACT } from "@/lib/sample-contract";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

/**
 * Uploads the bundled sample NDA through the real `/api/upload` endpoint and
 * routes into its workspace. Shared by the welcome flow and the empty-state
 * dashboard so "Try a sample" behaves identically wherever it appears.
 */
export function TrySampleButton({
  variant = "secondary",
  size = "md",
  className,
  label = "Try a sample NDA",
}: {
  variant?: React.ComponentProps<typeof Button>["variant"];
  size?: React.ComponentProps<typeof Button>["size"];
  className?: string;
  label?: string;
}) {
  const router = useRouter();
  const addDoc = useDocuments((s) => s.add);

  const run = useMutation({
    mutationFn: () => {
      const file = new File([SAMPLE_CONTRACT.text], SAMPLE_CONTRACT.filename, {
        type: "text/plain",
      });
      return uploadDocument(file);
    },
    onSuccess: (res: UploadResult) => {
      addDoc({
        id: res.document_id,
        filename: res.filename,
        contentType: res.content_type,
        uploadedAt: new Date().toISOString(),
        sensitivityTier: res.sensitivity.tier,
        clauseCount: res.count,
      });
      toast.success("Sample NDA ready", {
        description: `${res.count} clauses extracted — opening the workspace`,
      });
      router.push(`/documents/${res.document_id}`);
    },
    onError: () =>
      toast.error("Couldn't load the sample", {
        description: "Is the backend running? Check /models for status.",
      }),
  });

  return (
    <Button
      variant={variant}
      size={size}
      className={cn(className)}
      loading={run.isPending}
      onClick={() => run.mutate()}
    >
      {!run.isPending && <FlaskConical />}
      {run.isPending ? "Analysing sample…" : label}
    </Button>
  );
}
