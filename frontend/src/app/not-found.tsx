import Link from "next/link";
import { Compass } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Logo } from "@/components/layout/logo";

export default function NotFound() {
  return (
    <div className="flex min-h-dvh flex-col items-center justify-center gap-6 px-4 text-center">
      <Logo />
      <div className="flex size-14 items-center justify-center rounded-2xl bg-muted text-muted-foreground">
        <Compass className="size-7" />
      </div>
      <div className="space-y-2">
        <p className="text-sm font-medium text-subtle-foreground">404</p>
        <h1 className="text-2xl font-semibold tracking-tight">Page not found</h1>
        <p className="max-w-sm text-sm text-muted-foreground">
          The page you&rsquo;re looking for doesn&rsquo;t exist or has moved.
        </p>
      </div>
      <div className="flex gap-2">
        <Button asChild variant="secondary">
          <Link href="/">Go home</Link>
        </Button>
        <Button asChild>
          <Link href="/dashboard">Open the app</Link>
        </Button>
      </div>
    </div>
  );
}
