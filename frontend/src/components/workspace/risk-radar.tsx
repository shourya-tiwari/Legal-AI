"use client";

import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
} from "recharts";
import { titleCase } from "@/lib/format";

export function RiskRadar({
  categories,
  onSelect,
}: {
  categories: Record<string, number>;
  onSelect?: (category: string) => void;
}) {
  const data = Object.entries(categories).map(([k, v]) => ({
    category: titleCase(k),
    key: k,
    value: v,
  }));
  const max = Math.max(4, ...data.map((d) => d.value));

  return (
    <ResponsiveContainer width="100%" height={340}>
      <RadarChart data={data} outerRadius="72%">
        <PolarGrid stroke="var(--color-border)" />
        <PolarAngleAxis
          dataKey="category"
          tick={{
            fill: "var(--color-muted-foreground)",
            fontSize: 11,
          }}
        />
        <PolarRadiusAxis
          domain={[0, max]}
          tick={{ fill: "var(--color-subtle-foreground)", fontSize: 10 }}
          stroke="var(--color-border)"
        />
        <Radar
          name="Flags"
          dataKey="value"
          stroke="var(--color-primary)"
          fill="var(--color-primary)"
          fillOpacity={0.35}
          dot={{
            r: 3,
            fill: "var(--color-primary)",
            cursor: onSelect ? "pointer" : undefined,
          }}
          activeDot={{
            r: 5,
            onClick: (_: unknown, payload: unknown) => {
              const p = payload as { payload?: { key?: string } };
              if (p?.payload?.key && onSelect) onSelect(p.payload.key);
            },
          }}
        />
      </RadarChart>
    </ResponsiveContainer>
  );
}
