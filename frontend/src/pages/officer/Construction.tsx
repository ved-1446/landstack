import { Building2 } from "lucide-react";
import { Link } from "react-router";
import { Async } from "../../components/Async";
import { GlassCard, PageHeader } from "../../components/ui";
import { useAppData } from "../../lib/appData";
import { ConflictList } from "./Conflicts";

/** Construction: plots where the SIMULATED change check found a new building that is not in the records. */
export default function Construction() {
  const { conflicts } = useAppData();
  return (
    <section>
      <PageHeader eyebrow="OFFICER WORK DESK" title="New" emphasis="construction" subtitle="Plots where a new building shows up that the records do not mention." />
      <p className="mt-4 inline-flex items-center gap-2 rounded-pill border border-dashed border-sim px-3 py-1 font-mono text-11 tracking-wider text-sim">
        SIMULATED: there is no real satellite data. These come from two pretend surveys.
      </p>
      <GlassCard className="mt-6">
        <Async
          state={conflicts}
          what="the construction flags"
          isEmpty={(rows) => !rows || !rows.some((r) => r.findings.some((f) => f.type === "unrecorded_construction"))}
          empty={{ icon: Building2, title: "No new construction flagged", description: "The simulated survey comparison found no building that is missing from the records." }}
        >
          {(all) => {
            const rows = (all ?? []).filter((r) => r.findings.some((f) => f.type === "unrecorded_construction"));
            return (
              <>
                <p className="text-13 text-muted-on-navy" aria-live="polite">
                  {rows.length} {rows.length === 1 ? "plot" : "plots"}. Each adds 15 points. Switch on the simulated layer on the{" "}
                  <Link to="/app/map" className="text-cream underline underline-offset-4">
                    map
                  </Link>{" "}
                  to see the outlines.
                </p>
                <div className="mt-2">
                  <ConflictList rows={rows} label="Plots with a simulated new building" />
                </div>
              </>
            );
          }}
        </Async>
      </GlassCard>
    </section>
  );
}
