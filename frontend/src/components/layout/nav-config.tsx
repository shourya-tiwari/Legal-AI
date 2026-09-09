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
  Upload,
  Globe,
  Compass,
  type LucideIcon,
} from "lucide-react";

export interface NavItem {
  label: string;
  href: string;
  icon: LucideIcon;
  description?: string;
  /** exact-match highlight only (default: prefix match) */
  exact?: boolean;
  /** custom active-match predicate — wins over `exact`/prefix when set */
  match?: (pathname: string) => boolean;
  /** links out of the app (marketing route or external URL) */
  external?: boolean;
}

export interface NavGroup {
  label: string;
  items: NavItem[];
}

export const GITHUB_URL = "https://github.com/shourya-tiwari/Legal-AI";

/**
 * Primary application navigation. Four groups; `Resources` bridges to the
 * marketing layout so the user is never trapped inside the dashboard.
 */
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
        label: "Upload",
        href: "/documents/upload",
        icon: Upload,
        description: "Add a contract for analysis",
      },
      {
        label: "Documents",
        href: "/documents",
        icon: FileText,
        description: "Your contract library",
        // highlight for the library and any workspace, but not /documents/upload
        match: (p) => p === "/documents" || /^\/documents\/\d+/.test(p),
      },
      {
        label: "AI Assistant",
        href: "/assistant",
        icon: Sparkles,
        description: "Grounded Q&A over your contracts",
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

/**
 * Marketing pages surfaced *inside* the app sidebar. These navigate into the
 * `(marketing)` layout — the public header there always offers a one-click
 * route back to the dashboard.
 */
export const RESOURCES_NAV: NavItem[] = [
  {
    label: "Documentation",
    href: "/docs",
    icon: BookOpen,
    description: "Concepts and repository docs",
    external: true,
  },
  {
    label: "Architecture",
    href: "/architecture",
    icon: Workflow,
    description: "The full system design",
    external: true,
  },
  {
    label: "Research",
    href: "/research",
    icon: Microscope,
    description: "The five novelty directions",
    external: true,
  },
  {
    label: "About",
    href: "/about",
    icon: Info,
    description: "The engineering case study",
    external: true,
  },
];

/** Sidebar footer — settings + the routes that leave the app entirely. */
export const SETTINGS_NAV_ITEM: NavItem = {
  label: "Settings",
  href: "/settings",
  icon: Settings,
  description: "Playbook, appearance, local data",
};

export const WEBSITE_NAV_ITEM: NavItem = {
  label: "Back to website",
  href: "/",
  icon: Globe,
  description: "The marketing site",
  external: true,
};

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
  "/welcome",
  "/assistant",
  "/documents",
  "/documents/upload",
  "/review",
  "/knowledge-graph",
  "/evaluation",
  "/models",
  "/analytics",
  "/admin",
  "/settings",
  "/profile",
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

/** Marketing footer sections. */
export const FOOTER_SECTIONS: { title: string; links: NavItem[] }[] = [
  {
    title: "Product",
    links: [
      { label: "Features", href: "/features", icon: Layers },
      { label: "Architecture", href: "/architecture", icon: Workflow },
      { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
      { label: "AI Assistant", href: "/assistant", icon: Sparkles },
    ],
  },
  {
    title: "Platform",
    links: [
      { label: "Model Router", href: "/models", icon: Cpu },
      { label: "Evaluation", href: "/evaluation", icon: FlaskConical },
      { label: "Knowledge Graph", href: "/knowledge-graph", icon: Network },
      { label: "Review Queue", href: "/review", icon: ClipboardCheck },
    ],
  },
  {
    title: "Resources",
    links: [
      { label: "Documentation", href: "/docs", icon: BookOpen },
      { label: "Research", href: "/research", icon: Microscope },
      { label: "Get started", href: "/welcome", icon: Compass },
      { label: "Contact", href: "/contact", icon: Mail },
    ],
  },
  {
    title: "Project",
    links: [
      { label: "About the project", href: "/about", icon: Info },
      { label: "About the developer", href: "/about/developer", icon: Info },
      { label: "GitHub", href: GITHUB_URL, icon: Globe, external: true },
      {
        label: "License (MIT)",
        href: `${GITHUB_URL}/blob/main/LICENSE`,
        icon: FileText,
        external: true,
      },
    ],
  },
];
