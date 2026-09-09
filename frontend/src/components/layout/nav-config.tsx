import {
  LayoutDashboard,
  Sparkles,
  FileText,
  ShieldAlert,
  GitCompareArrows,
  Network,
  Workflow,
  ClipboardCheck,
  FlaskConical,
  Cpu,
  BarChart3,
  Settings,
  ShieldCheck,
  BookOpen,
  Home,
  Layers,
  Microscope,
  Info,
  Mail,
  type LucideIcon,
} from "lucide-react";

export interface NavItem {
  label: string;
  href: string;
  icon: LucideIcon;
  description?: string;
  /** exact-match highlight only (default: prefix match) */
  exact?: boolean;
}

export interface NavGroup {
  label: string;
  items: NavItem[];
}

export const APP_NAV: NavGroup[] = [
  {
    label: "Workspace",
    items: [
      {
        label: "Dashboard",
        href: "/dashboard",
        icon: LayoutDashboard,
        description: "Workspace overview",
        exact: true,
      },
      {
        label: "AI Assistant",
        href: "/assistant",
        icon: Sparkles,
        description: "Grounded Q&A over your contracts",
      },
      {
        label: "Documents",
        href: "/documents",
        icon: FileText,
        description: "Your contract library",
      },
    ],
  },
  {
    label: "Analysis",
    items: [
      {
        label: "Review Queue",
        href: "/review",
        icon: ClipboardCheck,
        description: "Analyses flagged for a human",
      },
      {
        label: "Knowledge Graph",
        href: "/knowledge-graph",
        icon: Network,
        description: "Portfolio-wide term & conflict explorer",
      },
      {
        label: "Evaluation",
        href: "/evaluation",
        icon: FlaskConical,
        description: "Model benchmarks & cutover gates",
      },
    ],
  },
  {
    label: "Platform",
    items: [
      {
        label: "Model Router",
        href: "/models",
        icon: Cpu,
        description: "Providers, hosting classes, routing",
      },
      {
        label: "Analytics",
        href: "/analytics",
        icon: BarChart3,
        description: "Usage, latency, egress",
      },
      {
        label: "Admin",
        href: "/admin",
        icon: ShieldCheck,
        description: "Users, policies, audit, health",
      },
    ],
  },
];

export const WORKSPACE_TABS = (id: number): NavItem[] => [
  { label: "Overview", href: `/documents/${id}`, icon: Layers, exact: true },
  { label: "Clauses", href: `/documents/${id}/clauses`, icon: FileText },
  { label: "Risk", href: `/documents/${id}/risk`, icon: ShieldAlert },
  { label: "Timeline", href: `/documents/${id}/timeline`, icon: Workflow },
  { label: "Negotiation", href: `/documents/${id}/negotiation`, icon: GitCompareArrows },
  { label: "Knowledge Graph", href: `/documents/${id}/graph`, icon: Network },
  { label: "Agents", href: `/documents/${id}/agents`, icon: Workflow },
  { label: "Ask", href: `/documents/${id}/ask`, icon: Sparkles },
];

export const ADMIN_TABS: NavItem[] = [
  { label: "Overview", href: "/admin", icon: ShieldCheck, exact: true },
  { label: "Users", href: "/admin/users", icon: ClipboardCheck },
  { label: "Models", href: "/admin/models", icon: Cpu },
  { label: "Egress Log", href: "/admin/egress", icon: ShieldAlert },
  { label: "Feature Flags", href: "/admin/flags", icon: Settings },
];

/**
 * Routes that have a real page shipped. The sidebar and command palette only
 * surface these; each milestone adds its routes here so no committed state
 * links to a 404. (Marketing routes are always considered ready — they render
 * from static content.)
 */
export const READY_ROUTES = new Set<string>([
  "/dashboard",
  "/assistant",
  "/documents",
  "/documents/upload",
  "/review",
  "/models",
]);

export function filterReadyNav(groups: NavGroup[]): NavGroup[] {
  return groups
    .map((g) => ({
      ...g,
      items: g.items.filter((i) => READY_ROUTES.has(i.href)),
    }))
    .filter((g) => g.items.length > 0);
}

export const MARKETING_NAV: NavItem[] = [
  { label: "Home", href: "/", icon: Home, exact: true },
  { label: "Features", href: "/features", icon: Layers },
  { label: "Architecture", href: "/architecture", icon: Workflow },
  { label: "Research", href: "/research", icon: Microscope },
  { label: "Docs", href: "/docs", icon: BookOpen },
  { label: "About", href: "/about", icon: Info },
  { label: "Contact", href: "/contact", icon: Mail },
];
