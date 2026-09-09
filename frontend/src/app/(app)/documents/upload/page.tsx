"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { toast } from "sonner";
import { FileCheck2, ShieldQuestion } from "lucide-react";
import { uploadDocument, type UploadResult } from "@/lib/api";
import { useDocuments } from "@/lib/stores/documents";
import { PageHeader, PageBody } from "@/components/layout/page-header";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Dropzone } from "@/components/shared/dropzone";
import { SensitivityBadge } from "@/components/shared/sensitivity-badge";
import { ErrorState } from "@/components/ui/error-state";

export default function UploadPage() {
  const router = useRouter();
  const addDoc = useDocuments((s) => s.add);
  const [file, setFile] = React.useState<File | null>(null);
  const [progress, setProgress] = React.useState(0);

  const upload = useMutation({
    mutationFn: (f: File) => uploadDocument(f, setProgress),
    onSuccess: (res: UploadResult) => {
      addDoc({
        id: res.document_id,
        filename: res.filename,
        contentType: res.content_type,
        uploadedAt: new Date().toISOString(),
        sensitivityTier: res.sensitivity.tier,
        clauseCount: res.count,
      });
      toast.success("Document uploaded", {
        description: `${res.count} clauses extracted`,
      });
      router.push(`/documents/${res.document_id}`);
    },
    onError: () => setProgress(0),
  });

  return (
    <>
      <PageHeader
        title="Upload a document"
        description="PDF, DOCX, TXT, or a scanned image. Extraction runs fully local — no cloud OCR."
        breadcrumbs={[
          { label: "Documents", href: "/documents" },
          { label: "Upload" },
        ]}
      />
      <PageBody className="max-w-2xl">
        <Card>
          <CardContent className="space-y-5 pt-5">
            <Dropzone
              file={file}
              onFile={(f) => {
                setFile(f);
                upload.reset();
              }}
              onClear={() => {
                setFile(null);
                setProgress(0);
                upload.reset();
              }}
              disabled={upload.isPending}
            />

            {upload.isPending && (
              <div className="space-y-2">
                <Progress value={progress} />
                <p className="text-xs text-muted-foreground">
                  {progress < 100
                    ? `Uploading… ${progress}%`
                    : "Extracting clauses and classifying sensitivity…"}
                </p>
              </div>
            )}

            {upload.isError && (
              <ErrorState error={upload.error} title="Upload failed" />
            )}

            {upload.isSuccess && (
              <div className="flex items-center gap-3 rounded-lg border border-success/30 bg-success/10 p-3 text-sm">
                <FileCheck2 className="size-4 text-success" />
                <span>Uploaded. Redirecting to the workspace…</span>
              </div>
            )}

            <div className="flex items-center justify-between">
              <p className="flex items-center gap-1.5 text-xs text-subtle-foreground">
                <ShieldQuestion className="size-3.5" />
                Sensitivity is classified automatically on upload.
              </p>
              <Button
                onClick={() => file && upload.mutate(file)}
                disabled={!file || upload.isPending}
                loading={upload.isPending}
              >
                Upload &amp; analyse
              </Button>
            </div>
          </CardContent>
        </Card>

        <div className="mt-4 grid grid-cols-2 gap-3 text-xs text-muted-foreground sm:grid-cols-4">
          {(["public", "internal", "confidential", "privileged"] as const).map(
            (tier) => (
              <div
                key={tier}
                className="flex flex-col items-start gap-1.5 rounded-lg border border-border bg-surface p-3"
              >
                <SensitivityBadge tier={tier} withTooltip={false} />
              </div>
            ),
          )}
        </div>
      </PageBody>
    </>
  );
}
