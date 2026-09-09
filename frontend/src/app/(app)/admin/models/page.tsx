"use client";

import * as React from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Plus, Trash2, ShieldOff } from "lucide-react";
import {
  getClassCOverrides,
  setClassCOverride,
  clearClassCOverride,
  getModelsStatus,
} from "@/lib/api";
import { qk } from "@/lib/query-keys";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { EmptyState } from "@/components/ui/empty-state";
import { ListSkeleton } from "@/components/shared/loaders";
import { relativeTime } from "@/lib/format";

const KNOWN_TASKS = [
  "qa",
  "clause_rewrite",
  "timeline_extract",
  "risk_analysis",
  "contextualize",
  "agent_summary",
  "agent_plan",
  "deontic_escalation",
  "clause_type_escalation",
];

export default function AdminModelsPage() {
  const qc = useQueryClient();
  const overrides = useQuery({
    queryKey: qk.classCOverrides,
    queryFn: getClassCOverrides,
    retry: false,
  });
  const status = useQuery({ queryKey: qk.modelsStatus, queryFn: getModelsStatus });

  const rows = overrides.data?.overrides ?? [];

  const toggle = useMutation({
    mutationFn: ({ task, disabled }: { task: string; disabled: boolean }) =>
      setClassCOverride(task, disabled, "toggled from the admin UI"),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.classCOverrides }),
    onError: (e) =>
      toast.error("Failed", {
        description: String(e).includes("admin")
          ? "Requires an admin role."
          : String(e),
      }),
  });

  const remove = useMutation({
    mutationFn: (task: string) => clearClassCOverride(task),
    onSuccess: () => {
      toast.success("Reverted to the static policy");
      qc.invalidateQueries({ queryKey: qk.classCOverrides });
    },
    onError: (e) => toast.error("Failed", { description: String(e) }),
  });

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader className="flex-row items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <ShieldOff className="size-4" /> Per-task Class-C kill switches
          </CardTitle>
          <AddOverrideDialog
            existing={rows.map((r) => r.task)}
            onAdd={(task) => toggle.mutate({ task, disabled: true })}
          />
        </CardHeader>
        <CardContent>
          <p className="mb-4 text-sm text-muted-foreground">
            An override can only <em>remove</em> a Class-C candidate the static
            policy already permitted for a task — it can never add one back, and
            it never weakens the unconditional confidential/privileged gate.
            Takes effect on the very next request.
          </p>
          {overrides.isLoading ? (
            <ListSkeleton rows={3} />
          ) : overrides.isError ? (
            <EmptyState
              icon={ShieldOff}
              title="Overrides unavailable"
              description="This endpoint requires a signed-in session. With AUTH_REQUIRED=false the static policy is the only policy."
            />
          ) : rows.length === 0 ? (
            <EmptyState
              icon={ShieldOff}
              title="No active overrides"
              description="Every task follows the static routing.yaml policy."
            />
          ) : (
            <ul className="divide-y divide-border">
              {rows.map((r) => (
                <li
                  key={r.task}
                  className="flex flex-wrap items-center gap-3 py-3"
                >
                  <span className="font-mono text-sm">{r.task}</span>
                  <Badge variant={r.class_c_disabled ? "danger" : "success"}>
                    Class C {r.class_c_disabled ? "disabled" : "allowed"}
                  </Badge>
                  {r.updated_at && (
                    <span className="text-xs text-subtle-foreground">
                      {relativeTime(r.updated_at)}
                    </span>
                  )}
                  <div className="ml-auto flex items-center gap-3">
                    <Switch
                      checked={r.class_c_disabled}
                      onCheckedChange={(v) =>
                        toggle.mutate({ task: r.task, disabled: v })
                      }
                      aria-label={`Toggle Class C for ${r.task}`}
                    />
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      onClick={() => remove.mutate(r.task)}
                      aria-label="Remove override"
                    >
                      <Trash2 />
                    </Button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Registered providers</CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="divide-y divide-border text-sm">
            {(status.data?.providers ?? []).map((p) => (
              <li key={p.name} className="flex items-center gap-3 py-2.5">
                <span className="font-mono text-xs">{p.name}</span>
                <Badge variant="outline">Class {p.hosting_class}</Badge>
                <span className="text-xs text-muted-foreground">
                  {(p.capabilities ?? []).join(", ")}
                </span>
                <Badge
                  variant={p.available ? "success" : "default"}
                  className="ml-auto"
                >
                  {p.available ? "reachable" : "not configured"}
                </Badge>
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}

function AddOverrideDialog({
  existing,
  onAdd,
}: {
  existing: string[];
  onAdd: (task: string) => void;
}) {
  const [open, setOpen] = React.useState(false);
  const [task, setTask] = React.useState("");
  const available = KNOWN_TASKS.filter((t) => !existing.includes(t));

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm" variant="secondary">
          <Plus /> Add
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Disable Class C for a task</DialogTitle>
        </DialogHeader>
        <div className="space-y-2">
          <Label>Task</Label>
          <Input
            value={task}
            onChange={(e) => setTask(e.target.value)}
            placeholder="task name"
            list="known-tasks"
          />
          <datalist id="known-tasks">
            {available.map((t) => (
              <option key={t} value={t} />
            ))}
          </datalist>
          <div className="flex flex-wrap gap-1.5 pt-1">
            {available.map((t) => (
              <button key={t} onClick={() => setTask(t)}>
                <Badge variant={task === t ? "primary" : "outline"}>{t}</Badge>
              </button>
            ))}
          </div>
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button
            disabled={!task.trim()}
            onClick={() => {
              onAdd(task.trim());
              setOpen(false);
              setTask("");
            }}
          >
            Disable Class C
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
