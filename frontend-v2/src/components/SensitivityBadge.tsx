// A persistent visual indicator of a document's sensitivity tier
// (docs/v2/FRONTEND.md "Security at the frontend layer": Privileged/
// Confidential documents render with a persistent indicator; the backend
// Model Router is what actually enforces the Class-C block, this is just
// the honest UI reflection of that server-side guarantee).
const TIER_STYLES: Record<string, string> = {
  public: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30",
  internal: "bg-blue-500/15 text-blue-300 border-blue-500/30",
  confidential: "bg-amber-500/15 text-amber-300 border-amber-500/30",
  privileged: "bg-red-500/15 text-red-300 border-red-500/30",
};

export function SensitivityBadge({
  tier,
  externalProvidersPermitted,
}: {
  tier: string;
  externalProvidersPermitted: boolean;
}) {
  const style = TIER_STYLES[tier] ?? TIER_STYLES.internal;
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium ${style}`}
      title={
        externalProvidersPermitted
          ? "This document may be routed to an external model provider for public/internal-tier tasks."
          : "This document never leaves self-hosted providers (Model Router Class-C gate)."
      }
    >
      {!externalProvidersPermitted && <span aria-hidden="true">🔒</span>}
      {tier}
    </span>
  );
}
