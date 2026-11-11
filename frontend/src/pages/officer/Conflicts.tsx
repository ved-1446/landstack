import { Building2, CircleCheck } from "lucide-react";
import { useMemo, useState } from "react";
import { useNavigate } from "react-router";
import { Async } from "../../components/Async";
import { BandChip, Chip, DataList, GlassCard, PageHeader } from "../../components/ui";
import { prettyType } from "../../constants";
import { useAppData } from "../../lib/appData";
import type { ConflictRow, ConflictType } from "../../types";

/** The plot list shared by the Conflicts and Construction pages: highest score first, reason chips, a click opens the passport. */
export function ConflictList({ rows, label }: { rows: ConflictRow[]; label: string }) {
  const navigate = useNavigate();
  return (
    <DataList
      label={label}
      rows={rows.map((row) => ({
        key: row.ulpin,
        onClick: () => navigate(`/app/plots/${row.ulpin}`),
        primary: (
          <span className="flex flex-wrap items-center gap-x-3 gap-y-1">
            <span className="font-mono">{row.ulpin}</span>
            <span className="text-muted-on-navy">{row.village}</span>
          </span>
        ),
        secondary: (
          <span className="flex flex-wrap gap-1">
            {row.findings.map((f) => (
              <Chip key={f.type} tone={f.simulated ? "sim" : "neutral"}>
                {prettyType(f.type)} +{f.points}
                {f.simulated ? " (simulated)" : ""}
              </Chip>
            ))}
          </span>
        ),
        trailing: (
          <span className="flex items-center gap-3">
            <BandChip band={row.band} />
            <span className="w-8 text-right font-serif text-26 text-cream">{row.score}</span>
          </span>
        ),
      }))}
    />
  );
}

/** Conflicts: every plot with at least one finding, filtered by the kind of finding. */
export default function Conflicts() {
  const { conflicts, types } = useAppData();
  const [type, setType] = useState<ConflictType | "all">("all");
  const order = useMemo(() => (types.data ?? []).map((t) => t.type), [types.data]);

  return (
    <section>
      <PageHeader eyebrow="OFFICER WORK DESK" title="Open" emphasis="conflicts" subtitle="Every plot where a check found something, highest score first. Pick a kind of problem to narrow the list." />
      <GlassCard className="mt-8">
        <Async
          state={conflicts}
          what="the conflicts"
          isEmpty={(rows) => !rows || rows.length === 0}
          empty={{ icon: CircleCheck, title: "No conflicts found", description: "None of the checks found a problem in any plot." }}
        >
          {(all) => {
            const rows = all ?? [];
            const count = (t: ConflictType) => rows.filter((r) => r.findings.some((f) => f.type === t)).length;
            const shown = type === "all" ? rows : rows.filter((r) => r.findings.some((f) => f.type === type));
            return (
              <>
                <div role="group" aria-label="Kind of problem" className="flex flex-wrap gap-2">
                  <Chip pressed={type === "all"} onClick={() => setType("all")} count={rows.length}>
                    All problems
                  </Chip>
                  {order.map((t) => (
                    <Chip key={t} pressed={type === t} onClick={() => setType(t)} count={count(t)} tone={types.data?.find((x) => x.type === t)?.simulated ? "sim" : "neutral"}>
                      {prettyType(t)}
                    </Chip>
                  ))}
                </div>
                <p className="mt-4 text-13 text-muted-on-navy" aria-live="polite">
                  {shown.length} {shown.length === 1 ? "plot" : "plots"}.
                </p>
                <div className="mt-2">
                  {shown.length === 0 ? (
                    <p className="flex items-center gap-2 py-6 text-14 text-muted-on-navy">
                      <Building2 className="size-5" aria-hidden="true" />
                      No plot has this kind of problem.
                    </p>
                  ) : (
                    <ConflictList rows={shown} label="Plots with conflicts" />
                  )}
                </div>
              </>
            );
          }}
        </Async>
      </GlassCard>
    </section>
  );
}
