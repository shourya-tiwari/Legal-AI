import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  compress: true,
  // The heavy client libraries (React Flow, Recharts) are already lazy-loaded
  // via next/dynamic at their call sites; this just trims the barrel imports.
  experimental: {
    optimizePackageImports: ["lucide-react", "recharts", "date-fns"],
  },
};

export default nextConfig;
