"use client";

import * as React from "react";
import {
  Scale,
  Tag,
  Link2,
  CalendarClock,
  AlertCircle,
  Wand2,
  Lightbulb,
} from "lucide-react";
import type { ClauseObject } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tooltip } from "@/components/ui/tooltip";
import { RewriteDialog } from "@/components/workspace/rewrite-dialog";
import { ContextualizeDialog } from "@/components/workspace/contextualize-dialog";
import { MODALITY_META, titleCase } from "@/lib/format";
import { cn } from "@/lib/utils";

export function DeonticBadge({
  modality,
  trigger,
  source,
}: {
  modality: string;
  trigger?: string;
  source?: string;
}) {
  const meta = MODALITY_META[modality] ?? MODALITY_META.none;
  return (
    <Tooltip
      content={
        <div className="space-y-0.5">
          <p className="font-medium">{meta.label}</p>
          {trigger && (
            <p className="text-muted-foreground">trigger: “{trigger}”</p>
          )}
          {source && <p className="text-muted-foreground">source: {source}</p>}
        </div>
      }
    >
      <Badge variant="outline" className={cn("gap-1", meta.className)}>
        <Scale />
        {meta.label}
      </Badge>
    </Tooltip>
  );
}

export function ClauseCard({
  clause,
  documentId,
}: {
  clause: ClauseObject;
  documentId: number;
}) {
  const c = clause;
  const deontic = c.deontic_tags ?? [];
  const entities = c.entities ?? [];
  const terms = c.defined_terms_used ?? [];
  const xrefs = c.cross_references ?? [];
  const temporal = c.temporal_expressions ?? [];
  const ambiguity = c.ambiguity_flags ?? [];

  return (
    <Card className="p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className="font-mono text-xs text-subtle-foreground">
            #{c.id}
          </span>
          <Badge variant="primary">{titleCase(c.clause_type)}</Badge>
          {c.clause_type_source === "ai" && (
            <Badge variant="info" className="text-[10px]">
              AI
            </Badge>
          )}
        </div>
        <div className="flex shrink-0 gap-1">
          <RewriteDialog
            documentId={documentId}
            blockId={c.id}
            original={c.text}
            trigger={
              <Button variant="ghost" size="icon-sm" aria-label="Rewrite clause">
                <Wand2 />
              </Button>
            }
          />
          <ContextualizeDialog
            documentId={documentId}
            blockId={c.id}
            clauseText={c.text}
            trigger={
              <Button
                variant="ghost"
                size="icon-sm"
                aria-label="Explain in my context"
              >
                <Lightbulb />
              </Button>
            }
          />
        </div>
      </div>

      <p className="mt-2.5 text-sm leading-relaxed text-muted-foreground">
        {c.text}
      </p>

      {(deontic.length > 0 ||
        entities.length > 0 ||
        terms.length > 0 ||
        xrefs.length > 0 ||
        temporal.length > 0 ||
        ambiguity.length > 0) && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {deontic.map((t, i) => (
            <DeonticBadge
              key={i}
              modality={t.modality}
              trigger={t.trigger_phrase}
              source={t.source}
            />
          ))}
          {terms.map((t) => (
            <Badge key={t} variant="default">
              <Tag />
              {t}
            </Badge>
          ))}
          {entities.slice(0, 6).map((e, i) => (
            <Badge key={i} variant="outline" className="text-subtle-foreground">
              {e.type}: {e.text}
            </Badge>
          ))}
          {xrefs.map((x, i) => (
            <Badge key={i} variant="default">
              <Link2 />
              {x.text}
            </Badge>
          ))}
          {temporal.map((t, i) => (
            <Badge key={i} variant="default">
              <CalendarClock />
              {t.text}
              {t.normalized_date && (
                <span className="text-subtle-foreground">
                  {" "}
                  → {t.normalized_date}
                </span>
              )}
            </Badge>
          ))}
          {ambiguity.map((a, i) => (
            <Tooltip key={i} content={a.explanation}>
              <Badge variant="warning">
                <AlertCircle />
                {a.term}
              </Badge>
            </Tooltip>
          ))}
        </div>
      )}
    </Card>
  );
}
