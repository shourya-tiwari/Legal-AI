import type { ReactNode } from "react";

/**
 * Remounts on every top-level navigation within the app, giving each page a
 * short enter transition so moving around the workspace feels continuous
 * rather than instant-swap. `prefers-reduced-motion` collapses the animation
 * via the global rule in `globals.css`.
 */
export default function AppTemplate({ children }: { children: ReactNode }) {
  return <div className="animate-page-in">{children}</div>;
}
