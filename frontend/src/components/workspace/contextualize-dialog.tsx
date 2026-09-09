"use client";

import * as React from "react";
import { useMutation } from "@tanstack/react-query";
import { Lightbulb } from "lucide-react";
import { contextualizeDocument } from "@/lib/api";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { ErrorState } from "@/components/ui/error-state";

const ROLES = [
  "employee",
  "employer",
  "tenant",
  "landlord",
  "contractor",
  "client",
  "consumer",
  "founder",
  "investor",
];
const TONES = ["plain", "cautious", "reassuring", "direct"];

export function ContextualizeDialog({
  documentId,
  blockId,
  clauseText,
  trigger,
}: {
  documentId: number;
  blockId: string | number;
  clauseText: string;
  trigger: React.ReactNode;
}) {
  const [open, setOpen] = React.useState(false);
  const [role, setRole] = React.useState("tenant");
  const [location, setLocation] = React.useState("");
  const [contractType, setContractType] = React.useState("");
  const [tone, setTone] = React.useState("plain");

  const explain = useMutation({
    mutationFn: () =>
      contextualizeDocument(documentId, blockId, {
        role,
        location: location || null,
        contract_type: contractType || null,
        interests: null,
        tone,
      }),
  });

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>{trigger}</DialogTrigger>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Lightbulb className="size-4 text-primary" />
            Explain for my situation
          </DialogTitle>
          <DialogDescription>
            A personalised explanation grounded in retrieved legal-knowledge
            entries.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-3 sm:grid-cols-2">
          <div className="space-y-1.5">
            <Label htmlFor="role">Your role</Label>
            <Select value={role} onValueChange={setRole}>
              <SelectTrigger id="role">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {ROLES.map((r) => (
                  <SelectItem key={r} value={r} className="capitalize">
                    {r}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="tone">Tone</Label>
            <Select value={tone} onValueChange={setTone}>
              <SelectTrigger id="tone">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {TONES.map((t) => (
                  <SelectItem key={t} value={t} className="capitalize">
                    {t}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="loc">Location (optional)</Label>
            <Input
              id="loc"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              placeholder="e.g. California"
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="ct">Contract type (optional)</Label>
            <Input
              id="ct"
              value={contractType}
              onChange={(e) => setContractType(e.target.value)}
              placeholder="e.g. residential lease"
            />
          </div>
        </div>

        <Button
          onClick={() => explain.mutate()}
          loading={explain.isPending}
          className="w-full"
        >
          <Lightbulb /> Explain
        </Button>

        {explain.isPending && (
          <div className="space-y-2 rounded-lg border border-border p-3">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-11/12" />
            <Skeleton className="h-4 w-2/3" />
          </div>
        )}
        {explain.isError && <ErrorState error={explain.error} />}
        {explain.data && (
          <div className="space-y-3">
            <div className="rounded-lg border border-border bg-background p-3">
              <p className="whitespace-pre-wrap text-sm">
                {explain.data.explanation}
              </p>
            </div>
            {explain.data.citation_warning && (
              <Alert variant="warning">
                <AlertDescription>
                  The model referenced a citation number it wasn&rsquo;t given —
                  treat specifics with caution.
                </AlertDescription>
              </Alert>
            )}
            {(explain.data.citations ?? []).length > 0 && (
              <div className="space-y-2">
                <p className="text-xs font-medium text-subtle-foreground">
                  Sources
                </p>
                {(explain.data.citations ?? []).map((cit, i) => {
                  const cc = cit as { text?: string; citation?: string | null };
                  return (
                    <div
                      key={i}
                      className="rounded-lg border border-border p-2.5 text-xs"
                    >
                      <p className="text-muted-foreground">{cc.text}</p>
                      {cc.citation && (
                        <Badge variant="outline" className="mt-1.5">
                          {cc.citation}
                        </Badge>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        <p className="text-xs text-subtle-foreground">
          Clause: <span className="italic">{clauseText.slice(0, 140)}…</span>
        </p>
      </DialogContent>
    </Dialog>
  );
}
