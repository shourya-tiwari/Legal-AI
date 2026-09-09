import { CheckCircle2, AlertTriangle, HelpCircle } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Tooltip } from "@/components/ui/tooltip";

export function FaithfulnessBadge({
  ok,
  method,
  unsupportedCount = 0,
}: {
  ok: boolean;
  method?: string;
  unsupportedCount?: number;
}) {
  const notChecked = method === "not_checked";
  const Icon = notChecked ? HelpCircle : ok ? CheckCircle2 : AlertTriangle;
  const variant = notChecked ? "default" : ok ? "success" : "warning";

  const methodLabel =
    method === "nli"
      ? "NLI entailment head"
      : method === "lexical_fallback"
        ? "lexical overlap (NLI head not installed)"
        : method === "not_checked"
          ? "no check ran"
          : method;

  return (
    <Tooltip
      content={
        <div className="space-y-1">
          <p className="font-medium">
            {notChecked
              ? "Faithfulness not verified"
              : ok
                ? "Faithful — claims are grounded"
                : "Faithfulness issues found"}
          </p>
          <p className="text-muted-foreground">Method: {methodLabel}</p>
          {unsupportedCount > 0 && (
            <p className="text-muted-foreground">
              {unsupportedCount} unsupported claim
              {unsupportedCount > 1 ? "s" : ""}
            </p>
          )}
        </div>
      }
    >
      <Badge variant={variant}>
        <Icon />
        {notChecked ? "Not checked" : ok ? "Faithful" : "Issues found"}
      </Badge>
    </Tooltip>
  );
}
