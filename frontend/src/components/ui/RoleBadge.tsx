import { Building2, ShieldCheck, UserRound, type LucideIcon } from "lucide-react";
import { cn } from "../../lib/cn";
import type { Role } from "../../types";

export const ROLE_IDENTITY: Record<Role, { label: string; area: string; icon: LucideIcon }> = {
  citizen: { label: "Citizen", area: "MY LAND", icon: UserRound },
  officer: { label: "Officer", area: "OFFICER WORK DESK", icon: Building2 },
  admin: { label: "Admin", area: "CONTROL ROOM", icon: ShieldCheck },
};

/** Who is signed in: an icon and the role in words. The area name ("MY LAND"...) is the page eyebrow. */
export function RoleBadge({ role, className }: { role: Role; className?: string }) {
  const { label, icon: Icon } = ROLE_IDENTITY[role];
  return (
    <span className={cn("inline-flex items-center gap-2 rounded-pill border border-glass-border bg-glass-fill px-3 py-1 font-mono text-11 tracking-wider text-cream", className)}>
      <Icon className="size-4" aria-hidden="true" />
      {label.toUpperCase()}
    </span>
  );
}
