"use client";

import { useState } from "react";
import type { ContextualizeContext } from "@/lib/api";

const ROLES = ["tenant", "landlord", "employee", "employer", "customer", "vendor", "reader"];
const CONTRACT_TYPES = ["", "lease", "employment", "mortgage", "saas", "service", "purchase"];
const TONES = ["plain", "lawyer", "exec"];

export function ContextualizeForm({
  onSubmit,
  pending,
}: {
  onSubmit: (context: ContextualizeContext) => void;
  pending: boolean;
}) {
  const [role, setRole] = useState("reader");
  const [location, setLocation] = useState("");
  const [contractType, setContractType] = useState("");
  const [tone, setTone] = useState("plain");

  return (
    <form
      className="flex flex-col gap-3 rounded-xl border border-white/10 bg-white/[0.04] p-3"
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit({
          role,
          location: location.trim() || null,
          contract_type: contractType || null,
          interests: null,
          tone,
        });
      }}
    >
      <div className="grid grid-cols-2 gap-3">
        <label className="flex flex-col gap-1 text-xs font-medium text-zinc-400">
          Your role
          <select
            className="rounded border border-zinc-700 bg-zinc-900 px-2 py-1 text-sm text-zinc-100"
            value={role}
            onChange={(e) => setRole(e.target.value)}
          >
            {ROLES.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-xs font-medium text-zinc-400">
          Location (optional)
          <input
            className="rounded border border-zinc-700 bg-zinc-900 px-2 py-1 text-sm text-zinc-100"
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            placeholder="e.g. California"
          />
        </label>
        <label className="flex flex-col gap-1 text-xs font-medium text-zinc-400">
          Contract type
          <select
            className="rounded border border-zinc-700 bg-zinc-900 px-2 py-1 text-sm text-zinc-100"
            value={contractType}
            onChange={(e) => setContractType(e.target.value)}
          >
            {CONTRACT_TYPES.map((t) => (
              <option key={t} value={t}>
                {t || "Select type"}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-xs font-medium text-zinc-400">
          Explanation style
          <select
            className="rounded border border-zinc-700 bg-zinc-900 px-2 py-1 text-sm text-zinc-100"
            value={tone}
            onChange={(e) => setTone(e.target.value)}
          >
            {TONES.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </label>
      </div>
      <button
        type="submit"
        disabled={pending}
        className="self-start rounded-full bg-gradient-to-r from-indigo-600 to-blue-600 px-4 py-1.5 text-sm font-semibold text-white shadow-sm shadow-indigo-200 transition-transform hover:scale-[1.03] disabled:opacity-50 disabled:from-zinc-300 disabled:to-zinc-300 disabled:shadow-none"
      >
        {pending ? "Explaining…" : "Explain this clause"}
      </button>
    </form>
  );
}
