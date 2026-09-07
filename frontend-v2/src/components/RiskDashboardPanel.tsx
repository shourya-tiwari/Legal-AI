"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getRiskDashboard, type RiskDashboardResponse } from "@/lib/api";

// docs/v2/ROADMAP.md Phase 8: "Risk Dashboard spider/radar chart (closes
// the V1 README promise)". A hand-rolled SVG radar chart rather than a new
// charting dependency -- eight fixed axes (app/services/risk_radar/rules.py
// ::RISK_CATEGORY_NAMES), one polygon, no library needed for something
// this size. Click a category to drill down into the clause-level flags
// that produced its count.

const SIZE = 260;
const CENTER = SIZE / 2;
const MAX_RADIUS = CENTER - 48; // leaves room for axis labels

function polarPoint(angleDeg: number, radius: number): [number, number] {
  const angleRad = ((angleDeg - 90) * Math.PI) / 180;
  return [CENTER + radius * Math.cos(angleRad), CENTER + radius * Math.sin(angleRad)];
}

function RadarChart({
  categories,
  selected,
  onSelect,
}: {
  categories: [string, number][];
  selected: string | null;
  onSelect: (category: string) => void;
}) {
  const n = categories.length;
  const maxValue = Math.max(1, ...categories.map(([, v]) => v));
  const angleStep = 360 / n;

  const ringLevels = [0.25, 0.5, 0.75, 1];
  const dataPoints = categories.map(([, value], i) =>
    polarPoint(i * angleStep, (value / maxValue) * MAX_RADIUS),
  );
  const dataPath = dataPoints.map((p) => p.join(",")).join(" ");

  return (
    <svg
      width={SIZE}
      height={SIZE}
      viewBox={`0 0 ${SIZE} ${SIZE}`}
      role="img"
      aria-label="Risk category radar chart"
      className="mx-auto"
    >
      {ringLevels.map((level) => {
        const points = categories
          .map((_, i) => polarPoint(i * angleStep, level * MAX_RADIUS).join(","))
          .join(" ");
        return (
          <polygon
            key={level}
            points={points}
            fill="none"
            stroke="currentColor"
            className="text-white/10"
            strokeWidth={1}
          />
        );
      })}

      {categories.map((_, i) => {
        const [x, y] = polarPoint(i * angleStep, MAX_RADIUS);
        return (
          <line
            key={i}
            x1={CENTER}
            y1={CENTER}
            x2={x}
            y2={y}
            stroke="currentColor"
            className="text-white/10"
            strokeWidth={1}
          />
        );
      })}

      <polygon
        points={dataPath}
        fill="rgba(248,113,113,0.25)"
        stroke="rgb(248,113,113)"
        strokeWidth={2}
      />
      {dataPoints.map(([x, y], i) => (
        <circle key={i} cx={x} cy={y} r={3} fill="rgb(248,113,113)" />
      ))}

      {categories.map(([name, value], i) => {
        const [labelX, labelY] = polarPoint(i * angleStep, MAX_RADIUS + 28);
        const isSelected = name === selected;
        return (
          <g key={name}>
            <text
              x={labelX}
              y={labelY}
              textAnchor="middle"
              dominantBaseline="middle"
              fontSize={9}
              className={isSelected ? "fill-red-300 font-semibold" : "fill-zinc-400"}
              style={{ cursor: "pointer" }}
              onClick={() => onSelect(name)}
            >
              {name.split(" & ")[0]}
            </text>
            <text
              x={labelX}
              y={labelY + 11}
              textAnchor="middle"
              fontSize={9}
              className="fill-zinc-600"
              style={{ cursor: "pointer" }}
              onClick={() => onSelect(name)}
            >
              ({value})
            </text>
          </g>
        );
      })}
    </svg>
  );
}

export function RiskDashboardPanel({ documentId }: { documentId: number }) {
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);

  const { data, isLoading, isError, error } = useQuery<RiskDashboardResponse>({
    queryKey: ["risk-dashboard", documentId],
    queryFn: () => getRiskDashboard(documentId),
  });

  const categories = data ? (Object.entries(data.categories) as [string, number][]) : [];
  const drillDown = selectedCategory
    ? (data?.clause_findings ?? []).filter((f) => f.category === selectedCategory)
    : [];

  return (
    <div className="flex flex-col gap-4 rounded-2xl border border-white/10 bg-white/[0.04] p-5 shadow-sm backdrop-blur">
      <div>
        <h2 className="text-sm font-semibold text-zinc-300">Risk dashboard</h2>
        <p className="text-xs text-zinc-500">
          Keyword risk flags across the whole document, grouped by category. Click a category to
          see which clauses triggered it.
        </p>
      </div>

      {isLoading && <p className="text-xs text-zinc-500">Loading…</p>}

      {isError && (
        <p role="alert" className="text-sm text-red-400">
          Error: {error instanceof Error ? error.message : String(error)}
        </p>
      )}

      {data && (
        <div className="flex flex-col items-center gap-4">
          <RadarChart categories={categories} selected={selectedCategory} onSelect={setSelectedCategory} />

          <p className="text-xs text-zinc-500">{data.total_flags} total flag(s) across 8 categories.</p>

          {selectedCategory && (
            <div className="w-full rounded-xl border border-white/10 bg-white/[0.02] p-3">
              <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-zinc-400">
                {selectedCategory} ({drillDown.length})
              </h4>
              {drillDown.length === 0 ? (
                <p className="text-xs text-zinc-500">No flags in this category.</p>
              ) : (
                <ul className="flex flex-col gap-2">
                  {drillDown.map((finding, i) => (
                    <li key={i} className="rounded-lg border border-white/10 bg-white/[0.02] p-2 text-xs">
                      <span className="rounded-full bg-red-500/15 px-2 py-0.5 font-medium text-red-300">
                        {finding.term}
                      </span>
                      <p className="mt-1 text-zinc-400">{finding.explanation}</p>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
