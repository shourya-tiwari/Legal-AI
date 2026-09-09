import { formatDistanceToNow, format, isValid, parseISO } from "date-fns";

export function relativeTime(iso?: string | null): string {
  if (!iso) return "—";
  const d = typeof iso === "string" ? parseISO(iso) : iso;
  if (!isValid(d)) return "—";
  return formatDistanceToNow(d, { addSuffix: true });
}

export function shortDate(iso?: string | null): string {
  if (!iso) return "—";
  const d = parseISO(iso);
  return isValid(d) ? format(d, "MMM d, yyyy") : "—";
}

export function dateTime(iso?: string | null): string {
  if (!iso) return "—";
  const d = parseISO(iso);
  return isValid(d) ? format(d, "MMM d, yyyy · HH:mm") : "—";
}

export function bytes(n?: number | null): string {
  if (n == null) return "—";
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(2)} MB`;
}

export function pct(n: number, digits = 0): string {
  return `${(n * 100).toFixed(digits)}%`;
}

export function ms(n?: number | null): string {
  if (n == null) return "—";
  if (n < 1000) return `${Math.round(n)} ms`;
  return `${(n / 1000).toFixed(2)} s`;
}

export function truncate(s: string, n = 120): string {
  return s.length > n ? `${s.slice(0, n).trimEnd()}…` : s;
}

export function titleCase(s: string): string {
  return s
    .replace(/[_-]+/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export function initials(name: string): string {
  const parts = name.trim().split(/[\s@.]+/).filter(Boolean);
  return (parts[0]?.[0] ?? "?").concat(parts[1]?.[0] ?? "").toUpperCase();
}

/** Deontic modality → display + color token */
export const MODALITY_META: Record<
  string,
  { label: string; className: string }
> = {
  obligation: { label: "Obligation", className: "text-danger" },
  prohibition: { label: "Prohibition", className: "text-warning" },
  permission: { label: "Permission", className: "text-info" },
  discretion: { label: "Discretion", className: "text-success" },
  none: { label: "None", className: "text-subtle-foreground" },
};

/** Sensitivity tier → display metadata */
export const SENSITIVITY_META: Record<
  string,
  { label: string; badge: "default" | "info" | "warning" | "danger"; blurb: string }
> = {
  public: {
    label: "Public",
    badge: "default",
    blurb: "Safe to route to any provider, including external APIs.",
  },
  internal: {
    label: "Internal",
    badge: "info",
    blurb: "Default tier. External providers allowed on public/internal only.",
  },
  confidential: {
    label: "Confidential",
    badge: "warning",
    blurb: "Never leaves the perimeter — self-hosted providers only.",
  },
  privileged: {
    label: "Privileged",
    badge: "danger",
    blurb: "Attorney-client privileged. Strictly self-hosted, always.",
  },
};

export const HOSTING_CLASS_META: Record<
  string,
  { label: string; badge: "default" | "info" | "warning"; blurb: string }
> = {
  A: { label: "Class A", badge: "default", blurb: "Deterministic / CPU" },
  B: { label: "Class B", badge: "info", blurb: "Self-hosted neural" },
  C: {
    label: "Class C",
    badge: "warning",
    blurb: "External provider API — leaves the perimeter",
  },
};
