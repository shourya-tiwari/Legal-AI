import Link from "next/link";
import { GithubIcon } from "@/components/shared/brand-icons";
import { Logo } from "./logo";

const COLUMNS: { title: string; links: { label: string; href: string }[] }[] = [
  {
    title: "Product",
    links: [
      { label: "Features", href: "/features" },
      { label: "Architecture", href: "/architecture" },
      { label: "Dashboard", href: "/dashboard" },
      { label: "AI Assistant", href: "/assistant" },
    ],
  },
  {
    title: "Platform",
    links: [
      { label: "Model Router", href: "/models" },
      { label: "Evaluation", href: "/evaluation" },
      { label: "Knowledge Graph", href: "/knowledge-graph" },
      { label: "Review Queue", href: "/review" },
    ],
  },
  {
    title: "Resources",
    links: [
      { label: "Documentation", href: "/docs" },
      { label: "Research", href: "/research" },
      { label: "About the project", href: "/about" },
      { label: "About the developer", href: "/about/developer" },
    ],
  },
  {
    title: "Company",
    links: [
      { label: "Contact", href: "/contact" },
      { label: "GitHub", href: "https://github.com/shourya-tiwari/Legal-AI" },
    ],
  },
];

export function PublicFooter() {
  return (
    <footer className="border-t border-border bg-surface/40">
      <div className="mx-auto w-full max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
        <div className="grid gap-10 lg:grid-cols-[1.4fr_repeat(4,1fr)]">
          <div className="space-y-3">
            <Logo />
            <p className="max-w-xs text-sm text-muted-foreground">
              Self-hosted legal contract intelligence. Every model call routed by
              sensitivity tier — privileged text never leaves the perimeter.
            </p>
            <a
              href="https://github.com/shourya-tiwari/Legal-AI"
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
            >
              <GithubIcon className="size-4" />
              View source
            </a>
          </div>
          {COLUMNS.map((col) => (
            <div key={col.title}>
              <p className="text-xs font-medium uppercase tracking-wider text-subtle-foreground">
                {col.title}
              </p>
              <ul className="mt-3 space-y-2">
                {col.links.map((l) => (
                  <li key={l.label}>
                    <Link
                      href={l.href}
                      className="text-sm text-muted-foreground transition-colors hover:text-foreground"
                    >
                      {l.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
        <div className="mt-10 flex flex-col items-center justify-between gap-3 border-t border-border pt-6 text-xs text-subtle-foreground sm:flex-row">
          <p>
            © {new Date().getFullYear()} LegalAI. A final-year / portfolio
            engineering project.
          </p>
          <p>Built with Next.js · FastAPI · self-hosted models.</p>
        </div>
      </div>
    </footer>
  );
}
