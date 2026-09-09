import Link from "next/link";
import { GithubIcon } from "@/components/shared/brand-icons";
import { Logo } from "./logo";
import { FOOTER_SECTIONS, GITHUB_URL } from "./nav-config";

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
              href={GITHUB_URL}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
            >
              <GithubIcon className="size-4" />
              View source
            </a>
          </div>
          {FOOTER_SECTIONS.map((col) => (
            <div key={col.title}>
              <p className="text-xs font-medium uppercase tracking-wider text-subtle-foreground">
                {col.title}
              </p>
              <ul className="mt-3 space-y-2">
                {col.links.map((l) => (
                  <li key={l.label}>
                    {l.external ? (
                      <a
                        href={l.href}
                        target="_blank"
                        rel="noreferrer"
                        className="text-sm text-muted-foreground transition-colors hover:text-foreground"
                      >
                        {l.label}
                      </a>
                    ) : (
                      <Link
                        href={l.href}
                        className="text-sm text-muted-foreground transition-colors hover:text-foreground"
                      >
                        {l.label}
                      </Link>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
        <div className="mt-10 flex flex-col items-center justify-between gap-3 border-t border-border pt-6 text-xs text-subtle-foreground sm:flex-row">
          <p>
            © {new Date().getFullYear()} LegalAI · MIT License · Built by{" "}
            <a
              href="https://github.com/shourya-tiwari"
              target="_blank"
              rel="noreferrer"
              className="font-medium text-muted-foreground transition-colors hover:text-foreground"
            >
              Shourya Tiwari
            </a>
          </p>
          <p>Built with Next.js · FastAPI · self-hosted models.</p>
        </div>
      </div>
    </footer>
  );
}
