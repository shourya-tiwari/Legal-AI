"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { uploadDocument } from "@/lib/api";
import { SiteHeader } from "@/components/SiteHeader";

const FEATURES = [
  { icon: "📝", label: "Plain-English rewrite", desc: "Legalese clauses translated into normal language." },
  { icon: "⚠️", label: "Risk scan", desc: "Keyword + AI detection of high-risk terms." },
  { icon: "🗓️", label: "Timeline", desc: "Every date, deadline, and obligation extracted." },
  { icon: "💬", label: "Ask questions", desc: "Grounded Q&A over the actual contract text." },
];

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function Home() {
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

      <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col items-center px-6 py-16">
        <h1 className="text-center text-3xl font-semibold tracking-tight text-zinc-900 sm:text-4xl">
          Understand any contract in minutes
        </h1>
        <p className="mt-3 max-w-xl text-center text-base text-zinc-500">
          Upload a contract to get a plain-English rewrite, a risk scan, a timeline, and
          per-clause explanations — powered by the document-first{" "}
          <code className="rounded bg-zinc-100 px-1 py-0.5 text-sm">/api/v2</code> API.
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
          className={`mt-10 flex w-full cursor-pointer flex-col items-center gap-3 rounded-2xl border-2 border-dashed px-8 py-14 text-center transition-colors ${
            isDragOver
              ? "border-blue-500 bg-blue-50"
              : "border-zinc-300 bg-white hover:border-zinc-400 hover:bg-zinc-50"
          }`}
        >
          <span className="text-4xl" aria-hidden="true">
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
          className="mt-6 w-full rounded-lg bg-blue-600 px-4 py-3 text-sm font-semibold text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-zinc-300"
        >
          {upload.isPending ? "Uploading & analyzing…" : "Analyze document"}
        </button>

        {upload.isError && (
          <p role="alert" className="mt-3 text-sm text-red-700">
            Error: {upload.error instanceof Error ? upload.error.message : String(upload.error)}
          </p>
        )}

        <div className="mt-16 grid w-full grid-cols-1 gap-4 sm:grid-cols-2">
          {FEATURES.map((f) => (
            <div
              key={f.label}
              className="flex items-start gap-3 rounded-xl border border-zinc-200 bg-white p-4"
            >
              <span className="text-xl" aria-hidden="true">
                {f.icon}
              </span>
              <div>
                <p className="text-sm font-semibold text-zinc-900">{f.label}</p>
                <p className="text-sm text-zinc-500">{f.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}
