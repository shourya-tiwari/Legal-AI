"use client";

import { useRouter } from "next/navigation";
import Link from "next/link";
import { LogIn, LogOut, BookOpen, Settings, User, Globe } from "lucide-react";
import { toast } from "sonner";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { logout } from "@/lib/api";
import { useAuthToken, useSession, clearSession } from "@/lib/stores/auth";
import { initials } from "@/lib/format";

export function UserMenu() {
  const token = useAuthToken();
  const session = useSession();
  const router = useRouter();

  if (!token) {
    return (
      <Button variant="secondary" size="sm" asChild>
        <Link href="/login">
          <LogIn />
          <span className="hidden sm:inline">Sign in</span>
        </Link>
      </Button>
    );
  }

  const label = session?.email ?? "Signed in";

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button
          className="rounded-full outline-none focus-visible:ring-2 focus-visible:ring-ring"
          aria-label="Account menu"
        >
          <Avatar>
            <AvatarFallback>{initials(label)}</AvatarFallback>
          </Avatar>
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuLabel className="flex flex-col gap-1 py-2 text-sm text-foreground">
          <span className="truncate font-medium">{label}</span>
          {session && (
            <span className="flex items-center gap-1.5 text-xs font-normal text-muted-foreground">
              {session.orgName}
              <Badge variant="outline" className="capitalize">
                {session.role}
              </Badge>
            </span>
          )}
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem asChild>
          <Link href="/profile">
            <User /> Profile
          </Link>
        </DropdownMenuItem>
        <DropdownMenuItem asChild>
          <Link href="/settings">
            <Settings /> Settings
          </Link>
        </DropdownMenuItem>
        <DropdownMenuItem asChild>
          <Link href="/docs">
            <BookOpen /> Documentation
          </Link>
        </DropdownMenuItem>
        <DropdownMenuItem asChild>
          <Link href="/">
            <Globe /> Marketing site
          </Link>
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem
          variant="danger"
          onClick={async () => {
            await logout().catch(() => {});
            clearSession();
            toast.success("Signed out");
            router.push("/");
          }}
        >
          <LogOut /> Sign out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
