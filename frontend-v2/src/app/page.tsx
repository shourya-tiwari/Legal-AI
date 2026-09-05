"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { uploadDocument } from "@/lib/api";

export default function Home() {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedName, setSelectedName] = useState<string | null>(null);

  const upload = useMutation({
    mutationFn: (file: File) => uploadDocument(file),
    onSuccess: (result) => {
      router.push(`/documents/${result.document_id}`);
    },
  });

  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-6 px-4">
      <div className="w-full max-w-lg rounded-xl border border-zinc-200 bg-white p-8 shadow-sm">
        <h1 className="mb-1 text-2xl font-semibold text-zinc-900">
          LegalAI Workspace
        </h1>
        <p className="mb-6 text-sm text-zinc-500">
          Upload a contract to get a plain-English rewrite, a risk scan, a
          timeline, and per-clause explanations — powered by the document-first{" "}
          <code className="rounded bg-zinc-100 px-1 py-0.5 text-xs">/api/v2</code>{" "}
          API.
        </p>

        <label
          htmlFor="fileInput"
          className="mb-1 block text-sm font-medium text-zinc-700"
        >
          Contract file (.pdf, .docx, .txt)
        </label>
        <input
          id="fileInput"
          ref={fileInputRef}
          type="file"
          accept=".pdf,.docx,.txt"
          onChange={(e) => setSelectedName(e.target.files?.[0]?.name ?? null)}
          className="mb-4 block w-full text-sm text-zinc-600 file:mr-3 file:rounded-md file:border-0 file:bg-zinc-100 file:px-3 file:py-1.5 file:text-sm file:font-medium hover:file:bg-zinc-200"
        />

        <button
          type="button"
          disabled={upload.isPending}
          onClick={() => {
            const file = fileInputRef.current?.files?.[0];
            if (file) upload.mutate(file);
          }}
          className="w-full rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {upload.isPending
            ? "Uploading & analyzing…"
            : selectedName
              ? `Analyze ${selectedName}`
              : "Select a file first"}
        </button>

        {upload.isError && (
          <p role="alert" className="mt-3 text-sm text-red-700">
            Error: {upload.error instanceof Error ? upload.error.message : String(upload.error)}
          </p>
        )}
      </div>
    </main>
  );
}
