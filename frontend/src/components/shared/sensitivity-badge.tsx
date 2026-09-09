import { Lock, ShieldCheck, ShieldAlert, Globe } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Tooltip } from "@/components/ui/tooltip";
import { SENSITIVITY_META } from "@/lib/format";

const ICONS = {
  public: Globe,
  internal: ShieldCheck,
  confidential: ShieldAlert,
  privileged: Lock,
} as const;

export function SensitivityBadge({
  tier,
  externalAllowed,
  withTooltip = true,
}: {
  tier: string;
  externalAllowed?: boolean;
  withTooltip?: boolean;
}) {
  const meta = SENSITIVITY_META[tier] ?? SENSITIVITY_META.internal;
  const Icon = ICONS[tier as keyof typeof ICONS] ?? ShieldCheck;

  const badge = (
    <Badge variant={meta.badge} className="capitalize">
      <Icon />
      {meta.label}
    </Badge>
  );

  if (!withTooltip) return badge;

  return (
    <Tooltip
      content={
        <div className="space-y-1">
          <p className="font-medium">{meta.label} tier</p>
          <p className="text-muted-foreground">{meta.blurb}</p>
          {externalAllowed !== undefined && (
            <p className="text-muted-foreground">
              External providers:{" "}
              <span className={externalAllowed ? "text-success" : "text-danger"}>
                {externalAllowed ? "permitted" : "blocked"}
              </span>
            </p>
          )}
        </div>
      }
    >
      <span className="inline-flex">{badge}</span>
    </Tooltip>
  );
}
