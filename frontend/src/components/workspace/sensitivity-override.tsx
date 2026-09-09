"use client";

import * as React from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { ShieldAlert } from "lucide-react";
import { overrideSensitivity } from "@/lib/api";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { DropdownMenuItem } from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { SENSITIVITY_META } from "@/lib/format";

const TIERS = ["public", "internal", "confidential", "privileged"] as const;

export function SensitivityOverrideDialog({
  documentId,
  current,
}: {
  documentId: number;
  current: string;
}) {
  const [open, setOpen] = React.useState(false);
  const [tier, setTier] = React.useState(current);
  const [reason, setReason] = React.useState("");
  const qc = useQueryClient();

  const mutate = useMutation({
    mutationFn: () => overrideSensitivity(documentId, tier, reason.trim()),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["sensitivity", documentId] });
      qc.invalidateQueries({ queryKey: ["document", documentId] });
      toast.success(`Sensitivity set to ${tier}`);
      setOpen(false);
      setReason("");
    },
    onError: (e) =>
      toast.error("Override failed", {
        description:
          String(e).includes("403") || String(e).includes("admin")
            ? "This action requires an admin role."
            : String(e),
      }),
  });

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DropdownMenuItem
        onSelect={(e) => {
          e.preventDefault();
          setTier(current);
          setOpen(true);
        }}
      >
        <ShieldAlert /> Override sensitivity
      </DropdownMenuItem>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Override sensitivity tier</DialogTitle>
          <DialogDescription>
            Admin only. The reason is recorded in the audit log. This changes
            which providers every model call for this document may reach.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="tier">Tier</Label>
            <Select value={tier} onValueChange={setTier}>
              <SelectTrigger id="tier">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {TIERS.map((t) => (
                  <SelectItem key={t} value={t}>
                    <span className="capitalize">{SENSITIVITY_META[t].label}</span>{" "}
                    — {SENSITIVITY_META[t].blurb}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="reason">Reason</Label>
            <Textarea
              id="reason"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Why this tier is correct…"
              rows={3}
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button
            onClick={() => mutate.mutate()}
            loading={mutate.isPending}
            disabled={!reason.trim() || tier === current}
          >
            Apply override
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
