// A persistent visual indicator of a document's sensitivity tier
// (docs/v2/FRONTEND.md "Security at the frontend layer": Privileged/
// Confidential documents render with a persistent indicator; the backend
// Model Router is what actually enforces the Class-C block, this is just
// the honest UI reflection of that server-side guarantee).
const TIER_STYLES: Record<string, string> = {
  public: "bg-emerald-100 text-emerald-800 border-emerald-300",
  internal: "bg-blue-100 text-blue-800 border-blue-300",
  confidential: "bg-amber-100 text-amber-900 border-amber-300",
  privileged: "bg-red-100 text-red-900 border-red-300",
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
