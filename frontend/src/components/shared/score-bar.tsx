import { cn } from "@/lib/utils";
import { pct } from "@/lib/format";

/** A compact candidate-vs-baseline score comparison bar. */
export function ScoreBar({
  score,
  baseline,
  passed,
}: {
  score: number;
  baseline?: number | null;
  passed?: boolean | null;
}) {
  const max = Math.max(score, baseline ?? 0, 0.001);
  return (
    <div className="w-full min-w-32 space-y-1">
      <div className="relative h-2 overflow-hidden rounded-full bg-muted">
        <div
          className={cn(
            "absolute inset-y-0 left-0 rounded-full",
            passed === false ? "bg-danger" : "bg-primary",
          )}
          style={{ width: `${(score / max) * 100}%` }}
        />
        {baseline != null && (
          <div
            className="absolute inset-y-0 w-0.5 bg-foreground"
            style={{ left: `${(baseline / max) * 100}%` }}
            title={`baseline ${pct(baseline, 1)}`}
          />
        )}
      </div>
      <div className="flex justify-between text-[10px] text-subtle-foreground">
        <span className="font-medium text-foreground">{pct(score, 1)}</span>
        {baseline != null && <span>baseline {pct(baseline, 1)}</span>}
      </div>
    </div>
  );
}
