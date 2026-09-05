import Link from "next/link";
import { SiteHeader } from "@/components/SiteHeader";

const FEATURES = [
  {
    icon: "📝",
    title: "Plain-English rewrite",
    desc: "Every clause translated out of legalese, whole-document or one clause at a time.",
  },
  {
    icon: "⚠️",
    title: "Risk radar",
    desc: "Keyword-based and AI-driven detection of high-risk terms — uncapped liability, unilateral termination, one-sided arbitration.",
  },
  {
    icon: "🗓️",
    title: "Timeline extraction",
    desc: "Every date, deadline, and time-based obligation pulled out and laid out in order.",
  },
  {
    icon: "🎯",
    title: "Contextualizer",
    desc: "Explanations personalized to your role, location, and the kind of contract you're reading.",
  },
  {
    icon: "💬",
    title: "Ask anything",
    desc: "Grounded Q&A over the actual contract text — no answer without a quote to back it up.",
  },
  {
    icon: "🤖",
    title: "Full agent analysis",
    desc: "A planner-driven pipeline that researches flagged clauses, checks cross-document conflicts, and verifies its own summary before you see it.",
  },
];

const STEPS = [
  { n: "1", title: "Upload", desc: "Drop in a .pdf, .docx, or .txt contract." },
  { n: "2", title: "Analyze", desc: "Every feature above runs against the document's extracted clauses." },
  { n: "3", title: "Understand", desc: "Read the plain-English version, the flagged risks, and the timeline — all in one workspace." },
];

export default function Home() {
  return (
    <div className="flex flex-1 flex-col">
      <SiteHeader />

      <main className="flex-1">
        {/* Hero */}
        <section className="mx-auto flex max-w-4xl flex-col items-center px-6 pt-20 pb-16 text-center">
          <span className="rounded-full border border-indigo-400/30 bg-indigo-500/10 px-3 py-1 text-xs font-semibold text-indigo-300">
            Document-first · powered by /api/v2
          </span>
          <h1 className="mt-5 text-4xl font-bold tracking-tight text-white sm:text-5xl">
            Understand any contract
            <br />
            <span className="bg-gradient-to-r from-indigo-400 to-blue-400 bg-clip-text text-transparent">
              in plain English
            </span>
          </h1>
          <p className="mt-5 max-w-xl text-base text-zinc-400 sm:text-lg">
            Upload a contract and get a plain-English rewrite, a risk scan, a timeline, and
            personalized clause explanations — grounded in the actual text, not a guess.
          </p>
          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <Link
              href="/upload"
              className="rounded-full bg-gradient-to-r from-indigo-500 to-blue-500 px-6 py-3 text-sm font-semibold text-white shadow-lg shadow-indigo-950 transition-transform hover:scale-[1.03]"
            >
              Upload a document →
            </Link>
            <Link
              href="/about"
              className="rounded-full border border-white/15 bg-white/5 px-6 py-3 text-sm font-semibold text-zinc-200 transition-colors hover:bg-white/10"
            >
              About this project
            </Link>
          </div>
        </section>

        {/* Feature grid */}
        <section className="mx-auto max-w-6xl px-6 py-16">
          <h2 className="text-center text-2xl font-semibold text-white">
            Everything the workspace does
          </h2>
          <p className="mx-auto mt-2 max-w-xl text-center text-sm text-zinc-500">
            Every one of these runs live once you upload a document — nothing here is a mockup.
          </p>
          <div className="mt-10 grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {FEATURES.map((f) => (
              <div
                key={f.title}
                className="group rounded-2xl border border-white/10 bg-white/[0.04] p-6 shadow-sm backdrop-blur transition-all hover:-translate-y-1 hover:border-indigo-400/30 hover:bg-white/[0.07]"
              >
                <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500/20 to-blue-500/20 text-xl">
                  {f.icon}
                </span>
                <h3 className="mt-4 text-base font-semibold text-zinc-100">{f.title}</h3>
                <p className="mt-1.5 text-sm text-zinc-400">{f.desc}</p>
              </div>
            ))}
          </div>
        </section>

        {/* How it works */}
        <section className="mx-auto max-w-4xl px-6 py-16">
          <h2 className="text-center text-2xl font-semibold text-white">How it works</h2>
          <div className="mt-10 grid grid-cols-1 gap-8 sm:grid-cols-3">
            {STEPS.map((s) => (
              <div key={s.n} className="flex flex-col items-center text-center">
                <span className="flex h-10 w-10 items-center justify-center rounded-full bg-gradient-to-br from-indigo-500 to-blue-500 text-sm font-bold text-white">
                  {s.n}
                </span>
                <h3 className="mt-3 text-sm font-semibold text-zinc-100">{s.title}</h3>
                <p className="mt-1 text-sm text-zinc-400">{s.desc}</p>
              </div>
            ))}
          </div>
        </section>

        {/* CTA banner */}
        <section className="mx-auto max-w-4xl px-6 pb-20">
          <div className="flex flex-col items-center gap-4 rounded-3xl bg-gradient-to-br from-indigo-500 to-blue-600 px-8 py-12 text-center shadow-xl shadow-indigo-950/50">
            <h2 className="text-2xl font-semibold text-white">Ready to try it?</h2>
            <p className="max-w-md text-sm text-indigo-100">
              No account needed for local development — upload a contract and see the whole
              workspace in action.
            </p>
            <Link
              href="/upload"
              className="mt-2 rounded-full bg-white px-6 py-3 text-sm font-semibold text-indigo-700 transition-transform hover:scale-[1.03]"
            >
              Upload a document →
            </Link>
          </div>
        </section>
      </main>
    </div>
  );
}
