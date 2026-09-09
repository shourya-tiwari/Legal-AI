import { Cpu, Server, Cloud } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Tooltip } from "@/components/ui/tooltip";
import { HOSTING_CLASS_META } from "@/lib/format";

const ICONS = { A: Cpu, B: Server, C: Cloud } as const;

export function HostingClassBadge({ hostingClass }: { hostingClass: string }) {
  const meta = HOSTING_CLASS_META[hostingClass];
  const Icon = ICONS[hostingClass as keyof typeof ICONS] ?? Cpu;
  if (!meta) return <Badge>{hostingClass}</Badge>;
  return (
    <Tooltip content={meta.blurb}>
      <Badge variant={meta.badge}>
        <Icon />
        {meta.label}
      </Badge>
    </Tooltip>
  );
}
