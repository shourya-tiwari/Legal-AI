"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { ArrowLeft, LogIn } from "lucide-react";
import { toast } from "sonner";
import { login } from "@/lib/api";
import { saveSession } from "@/lib/stores/auth";
import { Logo } from "@/components/layout/logo";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { ErrorState } from "@/components/ui/error-state";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = React.useState("");
  const [password, setPassword] = React.useState("");

  const submit = useMutation({
    mutationFn: () => login(email, password),
    onSuccess: (res) => {
      saveSession({
        orgName: res.org_name,
        role: res.role,
        expiresAt: res.expires_at,
        email,
      });
      toast.success(`Signed in to ${res.org_name}`);
      router.push("/dashboard");
    },
  });

  return (
    <div className="flex min-h-dvh flex-col items-center justify-center gap-6 px-4">
      <Logo />
      <Card className="w-full max-w-sm">
        <CardContent className="space-y-5 pt-6">
          <div className="space-y-1 text-center">
            <h1 className="text-lg font-semibold tracking-tight">Sign in</h1>
            <p className="text-sm text-muted-foreground">
              Only required when the backend runs with{" "}
              <code>AUTH_REQUIRED=true</code>.
            </p>
          </div>

          <Alert variant="info">
            <AlertDescription>
              In local development the API is open — you can{" "}
              <Link href="/dashboard" className="font-medium underline">
                skip straight to the app
              </Link>
              .
            </AlertDescription>
          </Alert>

          <form
            className="space-y-4"
            onSubmit={(e) => {
              e.preventDefault();
              submit.mutate();
            }}
          >
            <div className="space-y-1.5">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                autoComplete="username"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
            {submit.isError && (
              <ErrorState error={submit.error} title="Sign-in failed" />
            )}
            <Button
              type="submit"
              className="w-full"
              loading={submit.isPending}
            >
              <LogIn /> Sign in
            </Button>
          </form>
        </CardContent>
      </Card>
      <Button variant="ghost" size="sm" asChild>
        <Link href="/">
          <ArrowLeft /> Back to site
        </Link>
      </Button>
    </div>
  );
}
