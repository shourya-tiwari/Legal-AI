"use client";

import * as React from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { UserPlus, UserX, Users } from "lucide-react";
import { listUsers, createUser, revokeUser } from "@/lib/api";
import { qk } from "@/lib/query-keys";
import { useAuthToken } from "@/lib/stores/auth";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { TableSkeleton } from "@/components/shared/loaders";
import { ErrorState } from "@/components/ui/error-state";
import { EmptyState } from "@/components/ui/empty-state";
import { relativeTime } from "@/lib/format";

export default function AdminUsersPage() {
  const token = useAuthToken();
  const qc = useQueryClient();
  const q = useQuery({
    queryKey: qk.users,
    queryFn: listUsers,
    retry: false,
    enabled: !!token,
  });

  const users = q.data?.users ?? [];

  const revoke = useMutation({
    mutationFn: (id: number) => revokeUser(id),
    onSuccess: () => {
      toast.success("Session revoked");
      qc.invalidateQueries({ queryKey: qk.users });
    },
    onError: (e) => toast.error("Failed", { description: String(e) }),
  });

  if (!token) {
    return (
      <Alert variant="info">
        <AlertDescription>
          User management requires a signed-in admin session. When the backend
          runs with <code>AUTH_REQUIRED=false</code> there are no users — every
          caller is the shared default org.
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-end">
        <CreateUserDialog
          onCreated={() => qc.invalidateQueries({ queryKey: qk.users })}
        />
      </div>
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Users className="size-4" /> Org users
          </CardTitle>
        </CardHeader>
        <CardContent>
          {q.isLoading ? (
            <TableSkeleton />
          ) : q.isError ? (
            <ErrorState
              error={q.error}
              title="Could not load users"
              onRetry={() => q.refetch()}
            />
          ) : users.length === 0 ? (
            <EmptyState
              icon={Users}
              title="No users yet"
              description="Create the org's first user — the same shape create_api_key.py has for keys."
            />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Email</TableHead>
                  <TableHead>Role</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead />
                </TableRow>
              </TableHeader>
              <TableBody>
                {users.map((u) => (
                  <TableRow key={u.id}>
                    <TableCell className="font-medium">{u.email}</TableCell>
                    <TableCell>
                      <Badge variant="outline" className="capitalize">
                        {u.role}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {relativeTime(u.created_at)}
                    </TableCell>
                    <TableCell>
                      {u.revoked_at ? (
                        <Badge variant="danger">revoked</Badge>
                      ) : (
                        <Badge variant="success">active</Badge>
                      )}
                    </TableCell>
                    <TableCell className="text-right">
                      {!u.revoked_at && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => revoke.mutate(u.id)}
                        >
                          <UserX /> Revoke
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function CreateUserDialog({ onCreated }: { onCreated: () => void }) {
  const [open, setOpen] = React.useState(false);
  const [email, setEmail] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [role, setRole] = React.useState("editor");

  const create = useMutation({
    mutationFn: () => createUser(email, password, role),
    onSuccess: () => {
      toast.success("User created");
      setOpen(false);
      setEmail("");
      setPassword("");
      onCreated();
    },
    onError: (e) => toast.error("Failed", { description: String(e) }),
  });

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm">
          <UserPlus /> New user
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create a user</DialogTitle>
        </DialogHeader>
        <div className="space-y-3">
          <div className="space-y-1.5">
            <Label htmlFor="e">Email</Label>
            <Input
              id="e"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="p">Password (min 8)</Label>
            <Input
              id="p"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="r">Role</Label>
            <Select value={role} onValueChange={setRole}>
              <SelectTrigger id="r">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="admin">Admin</SelectItem>
                <SelectItem value="editor">Editor</SelectItem>
                <SelectItem value="viewer">Viewer</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button
            onClick={() => create.mutate()}
            loading={create.isPending}
            disabled={!email || password.length < 8}
          >
            Create
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
