import { AlertTriangle, Building2, Copy, FileX, Files, Receipt, Ruler, ShieldAlert, Users, type LucideIcon } from "lucide-react";
import { prettyType } from "../../constants";
import { Chip } from "./Chip";
import { cn } from "../../lib/cn";
import type { ConflictType } from "../../types";

// one icon per kind of conflict
const ICONS: Record<ConflictType, LucideIcon> = {
  boundary_overlap: Copy,
  owner_mismatch: Users,
  tax_overdue: Receipt,
  restricted_zone_clash: ShieldAlert,
  area_mismatch: Ruler,
  duplicate_survey_no: Files,
  invalid_boundary: AlertTriangle,
  missing_record: FileX,
  unrecorded_construction: Building2,
};

interface EvidenceCardProps {
  type: ConflictType;
  points: number;
  /** the finding's evidence text, exactly as the API returns it */
  evidence: string;
  /** the rule behind this kind of conflict (its description from /conflict-types), shown as the mono line */
  rule?: string;
  /** true when the data behind this finding is SIMULATED: a visible "Simulated" chip is shown */
  simulated?: boolean;
  className?: string;
}

/** One conflict on the cream sheet: icon chip, title, points pill, the evidence, and the rule it comes from. */
export function EvidenceCard({ type, points, evidence, rule, simulated = false, className }: EvidenceCardProps) {
  const Icon = ICONS[type];
  return (
    <article className={cn("rounded-card border border-line-on-cream bg-paper p-3", className)}>
      <header className="flex items-center gap-3">
        <span className="flex size-8 shrink-0 items-center justify-center rounded-control bg-ink text-paper">
          <Icon className="size-4" aria-hidden="true" />
        </span>
        <h3 className="min-w-0 flex-1 text-14 font-semibold text-ink">{prettyType(type)}</h3>
        {simulated && (
          <Chip surface="cream" tone="sim">
            Simulated
          </Chip>
        )}
        <span className="rounded-pill border border-line-on-cream px-2 py-1 font-mono text-12 font-medium text-ink">+{points}</span>
      </header>
      <p className="mt-2 text-13 text-muted-on-cream">{evidence}</p>
      {rule && <p className="mt-2 font-mono text-11 text-faint-on-cream">Rule: {rule}</p>}
    </article>
  );
}
