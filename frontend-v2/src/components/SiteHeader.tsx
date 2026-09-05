import Link from "next/link";

export function SiteHeader() {
  return (
    <header className="border-b border-zinc-200 bg-white">
      <div className="mx-auto flex h-14 w-full max-w-6xl items-center px-6">
        <Link href="/" className="flex items-center gap-2 text-sm font-semibold text-zinc-900">
          <span className="flex h-6 w-6 items-center justify-center rounded-md bg-blue-600 text-xs font-bold text-white">
            L
          </span>
          LegalAI
        </Link>
      </div>
    </header>
  );
}
