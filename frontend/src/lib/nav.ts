import type { NavLinkItem } from "../components/ui/GlassNav";
import type { Role } from "../types";

/** Where each role lands after signing in. */
export const HOME: Record<Role, string> = { citizen: "/app/plots", officer: "/app/dashboard", admin: "/app/dashboard" };

/** The pages a visitor can open (no login). "Check a plot" is a section of the home page. */
export const VISITOR_LINKS: NavLinkItem[] = [
  { to: "/", label: "Home", end: true },
  { to: "/#check", label: "Check a plot", plain: true },
  { to: "/verify", label: "Verify a passport" },
  { to: "/how-it-works", label: "How it works" },
  { to: "/about", label: "About" },
];

const WORK_DESK: NavLinkItem[] = [
  { to: "/app/plots", label: "Plots" },
  { to: "/app/map", label: "Map" },
  { to: "/app/conflicts", label: "Conflicts" },
  { to: "/app/construction", label: "Construction" },
  { to: "/app/zones", label: "Zones" },
];

const CITIZEN: NavLinkItem[] = [
  { to: "/app/home", label: "Home" },
  { to: "/app/plots", label: "My plots" },
  { to: "/app/map", label: "Map" },
  { to: "/app/verify", label: "Verify" },
  { to: "/app/activity", label: "Activity" },
];

const OFFICER: NavLinkItem[] = [{ to: "/app/dashboard", label: "Dashboard" }, ...WORK_DESK];

// the admin reaches the officer dashboard from the Work desk strip (its own Overview is a different page)
const ADMIN_DESK: NavLinkItem[] = [{ to: "/app/desk", label: "Dashboard" }, ...WORK_DESK];

const ADMIN: NavLinkItem[] = [
  { to: "/app/dashboard", label: "Overview" },
  { to: "/app/audit", label: "Audit log" },
  { to: "/app/users", label: "Users" },
  { to: "/app/system", label: "System" },
  { to: "/app/insights", label: "Insights" },
];

export interface RoleNav {
  /** the tabs in the top bar */
  links: NavLinkItem[];
  /** admin only: a second tab strip with the officer pages */
  workDesk?: NavLinkItem[];
}

export function navFor(role: Role): RoleNav {
  if (role === "citizen") return { links: CITIZEN };
  if (role === "officer") return { links: OFFICER };
  return { links: ADMIN, workDesk: ADMIN_DESK };
}

/** Pages a role may open that are not tabs: the Land Guide full page (its button is bottom-right), and "My activity" in the staff account menu. */
const EXTRA: Record<Role, string[]> = { citizen: ["/app/guide"], officer: ["/app/activity", "/app/guide"], admin: ["/app/activity", "/app/guide"] };

/** Every /app path this role may open. The server still decides what data it gets; this only decides which page is shown. */
export function allowedPaths(role: Role): string[] {
  const nav = navFor(role);
  return [...nav.links, ...(nav.workDesk ?? [])].map((l) => l.to).concat(EXTRA[role]);
}

/** Is this URL one of the role's pages? A plot passport (/app/plots/MH...) belongs to its list page's role. */
export function mayOpen(role: Role, pathname: string): boolean {
  const path = pathname.replace(/\/+$/, "");
  return allowedPaths(role).some((allowed) => path === allowed || path.startsWith(allowed + "/"));
}
