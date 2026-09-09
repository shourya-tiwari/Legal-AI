import type { Metadata, Viewport } from "next";
import { Providers } from "@/components/providers";
import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL("https://legalai.local"),
  title: {
    default: "LegalAI — Self-hosted legal contract intelligence",
    template: "%s · LegalAI",
  },
  description:
    "A self-hosted Legal-AI platform: clause extraction, risk analysis, plain-English rewrites, a planner-driven agent pipeline with faithfulness verification, a knowledge graph, and negotiation drafting — with every model call routed by sensitivity tier.",
  applicationName: "LegalAI",
  keywords: [
    "legal AI",
    "contract analysis",
    "clause extraction",
    "risk analysis",
    "knowledge graph",
    "self-hosted LLM",
  ],
  authors: [{ name: "LegalAI" }],
  icons: { icon: "/favicon.ico" },
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#fafafa" },
    { media: "(prefers-color-scheme: dark)", color: "#0d0d12" },
  ],
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" suppressHydrationWarning className="h-full antialiased">
      <body className="min-h-full font-sans">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
