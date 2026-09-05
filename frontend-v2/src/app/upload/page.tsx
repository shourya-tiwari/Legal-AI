"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { uploadDocument } from "@/lib/api";
import { SiteHeader } from "@/components/SiteHeader";

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function UploadPage() {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);

  const upload = useMutation({
    mutationFn: (f: File) => uploadDocument(f),
    onSuccess: (result) => {
      router.push(`/documents/${result.document_id}`);
    },
  });

  function pickFile(f: File | undefined | null) {
    if (f) setFile(f);
  }

  return (
    <div className="flex flex-1 flex-col">
      <SiteHeader />

      <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col items-center px-6 py-16">
        <span className="rounded-full bg-indigo-100 px-3 py-1 text-xs font-semibold text-indigo-700">
          Step 1 of 1
        </span>
        <h1 className="mt-4 text-center text-3xl font-semibold tracking-tight text-zinc-900">
          Upload your contract
        </h1>
        <p className="mt-2 max-w-md text-center text-sm text-zinc-500">
          Every feature — rewrite, risk scan, timeline, contextualizer, and the full agent
          analysis — runs against this one document next.
        </p>

        <div
          role="button"
          tabIndex={0}
          onClick={() => fileInputRef.current?.click()}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") fileInputRef.current?.click();
          }}
          onDragOver={(e) => {
            e.preventDefault();
            setIsDragOver(true);
          }}
          onDragLeave={() => setIsDragOver(false)}
          onDrop={(e) => {
            e.preventDefault();
            setIsDragOver(false);
            pickFile(e.dataTransfer.files?.[0]);
          }}
          className={`mt-8 flex w-full cursor-pointer flex-col items-center gap-3 rounded-2xl border-2 border-dashed px-8 py-16 text-center shadow-sm transition-all ${
            isDragOver
              ? "scale-[1.01] border-indigo-500 bg-indigo-50"
              : "border-zinc-300 bg-white/80 hover:border-indigo-400 hover:bg-indigo-50/40"
          }`}
        >
          <span className="flex h-14 w-14 items-center justify-center rounded-full bg-indigo-100 text-2xl" aria-hidden="true">
            📄
          </span>
          {file ? (
            <div>
              <p className="font-medium text-zinc-900">{file.name}</p>
              <p className="text-sm text-zinc-500">{formatSize(file.size)} — click to change</p>
            </div>
          ) : (
            <div>
              <p className="font-medium text-zinc-900">
                Drop a contract here, or click to browse
              </p>
              <p className="text-sm text-zinc-500">Supports .pdf, .docx, .txt</p>
            </div>
          )}
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.docx,.txt"
            className="sr-only"
            onChange={(e) => pickFile(e.target.files?.[0])}
          />
        </div>

        <button
          type="button"
          disabled={!file || upload.isPending}
          onClick={() => file && upload.mutate(file)}
          className="mt-6 w-full rounded-full bg-gradient-to-r from-indigo-600 to-blue-600 px-4 py-3 text-sm font-semibold text-white shadow-md shadow-indigo-200 transition-transform hover:scale-[1.01] disabled:cursor-not-allowed disabled:from-zinc-300 disabled:to-zinc-300 disabled:shadow-none"
        >
          {upload.isPending ? "Uploading & analyzing…" : "Analyze document"}
        </button>

        {upload.isError && (
          <p role="alert" className="mt-3 text-sm text-red-700">
            Error: {upload.error instanceof Error ? upload.error.message : String(upload.error)}
          </p>
        )}
      </main>
    </div>
  );
}
