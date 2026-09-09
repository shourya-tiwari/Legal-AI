import Link from "next/link";
import { SiteHeader } from "@/components/SiteHeader";

const STACK = [
  { label: "Backend", value: "FastAPI, SQLAlchemy, LangGraph" },
  { label: "AI", value: "Provider-agnostic Model Router — self-hosted by default, Gemini as an optional plugin" },
  { label: "Retrieval", value: "Hybrid RAG (BM25 + dense + Memgraph knowledge graph, RRF fusion)" },
  { label: "Frontend", value: "Next.js, TypeScript, Tailwind, TanStack Query" },
];

export default function AboutPage() {
  return (
    <div className="flex flex-1 flex-col">
      <SiteHeader />

      <main className="mx-auto w-full max-w-3xl flex-1 px-6 py-16">
        <h1 className="text-3xl font-semibold tracking-tight text-white">About this project</h1>

        <p className="mt-5 text-base leading-relaxed text-zinc-400">
          Legal contracts are often written in dense jargon that&apos;s hard for non-lawyers to
          parse. <strong className="font-semibold text-zinc-100">LegalAI</strong> (also known as
          Legal Demystifier / PlainSpeak AI) is an AI-native platform that uploads a contract and:
        </p>
        <ul className="mt-4 flex flex-col gap-2 text-sm text-zinc-400">
          {[
            "Rewrites clauses in plain English",
            "Extracts a structural map and timeline of dates and obligations",
            "Scans for risky clauses with rule-based and AI detection",
            "Answers free-form questions grounded in the contract text",
            "Runs a planner-driven multi-agent pipeline that researches, cross-checks, and verifies its own summary before showing it to you",
          ].map((line) => (
            <li key={line} className="flex gap-2">
              <span className="mt-1 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-indigo-400" />
              {line}
            </li>
          ))}
        </ul>

        <p className="mt-4 text-base leading-relaxed text-zinc-400">
          It&apos;s built self-hosted-first: every AI call goes through a Model Router that
          defaults to open, locally-servable models and treats a commercial API as an optional,
          swappable plugin — never a hard dependency. Documents are also tiered by sensitivity
          (public / internal / confidential / privileged), and that tier is enforced at the
          routing layer, not just documented as a policy.
        </p>

        <div className="mt-10 rounded-2xl border border-white/10 bg-white/[0.04] p-6 shadow-sm backdrop-blur">
          <h2 className="text-sm font-semibold text-zinc-100">Stack</h2>
          <dl className="mt-3 flex flex-col gap-3">
            {STACK.map((row) => (
              <div key={row.label} className="flex flex-col gap-0.5 sm:flex-row sm:gap-4">
                <dt className="w-28 flex-shrink-0 text-xs font-semibold uppercase tracking-wide text-zinc-500">
                  {row.label}
                </dt>
                <dd className="text-sm text-zinc-400">{row.value}</dd>
              </div>
            ))}
          </dl>
        </div>

        <div className="mt-10 flex items-center gap-4 rounded-2xl border border-white/10 bg-white/[0.04] p-6 shadow-sm backdrop-blur">
          <span className="flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-indigo-500 to-blue-500 text-lg font-bold text-white">
            ST
          </span>
          <div>
            <p className="text-sm font-semibold text-zinc-100">Built by Shourya Tiwari</p>
            <a
              href="https://github.com/shourya-tiwari/Legal-AI"
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-indigo-400 hover:underline"
            >
              github.com/shourya-tiwari/Legal-AI
            </a>
          </div>
        </div>

        <Link href="/upload" className="mt-10 inline-block text-sm font-semibold text-indigo-400 hover:underline">
          ← Try it out
        </Link>
      </main>
    </div>
  );
}
