"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { LogOut, ShieldCheck, Clock } from "lucide-react";
import { toast } from "sonner";
import { logout } from "@/lib/api";
import { useAuthToken, useSession, clearSession } from "@/lib/stores/auth";
import { PageHeader, PageBody } from "@/components/layout/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { initials, dateTime } from "@/lib/format";

export default function ProfilePage() {
  const token = useAuthToken();
  const session = useSession();
  const router = useRouter();

  return (
    <>
      <PageHeader
        title="Profile"
        description="Your session, organisation, and role."
        breadcrumbs={[{ label: "Settings", href: "/settings" }, { label: "Profile" }]}
      />
      <PageBody className="max-w-2xl space-y-6">
        {!token ? (
          <Alert variant="info">
            <AlertDescription>
              You&rsquo;re not signed in. The backend is running open
              (<code>AUTH_REQUIRED=false</code>) or you haven&rsquo;t logged in
              yet.{" "}
              <Link href="/login" className="font-medium underline">
                Sign in
              </Link>
              .
            </AlertDescription>
          </Alert>
        ) : (
          <>
            <Card>
              <CardContent className="flex items-center gap-4 pt-6">
                <Avatar className="size-14">
                  <AvatarFallback className="text-lg">
                    {initials(session?.email ?? "?")}
                  </AvatarFallback>
                </Avatar>
                <div className="space-y-1">
                  <p className="text-base font-semibold">
                    {session?.email ?? "Signed in"}
                  </p>
                  {session && (
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      {session.orgName}
                      <Badge variant="outline" className="capitalize">
                        <ShieldCheck /> {session.role}
                      </Badge>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Session</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 text-sm">
                <div className="flex items-center justify-between">
                  <span className="flex items-center gap-1.5 text-muted-foreground">
                    <Clock className="size-3.5" /> Expires
                  </span>
                  <span>{dateTime(session?.expiresAt)}</span>
                </div>
                <p className="text-xs text-subtle-foreground">
                  There is no self-serve password reset — an admin re-issues
                  credentials.
                </p>
              </CardContent>
            </Card>

            <Button
              variant="danger"
              onClick={async () => {
                await logout().catch(() => {});
                clearSession();
                toast.success("Signed out");
                router.push("/");
              }}
            >
              <LogOut /> Sign out
            </Button>
          </>
        )}
      </PageBody>
    </>
  );
}
