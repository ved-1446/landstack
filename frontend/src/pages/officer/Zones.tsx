import { MapPinOff } from "lucide-react";
import { getZones } from "../../api";
import { Async } from "../../components/Async";
import { BarList, GlassCard, PageHeader } from "../../components/ui";
import { prettyType } from "../../constants";
import { useFetch } from "../../hooks";
import { sqm } from "../../lib/format";
import type { ZoneRow } from "../../types";

type Ring = number[][];
const outer = (z: ZoneRow): Ring[] => {
  const c = z.geometry.coordinates as unknown;
  return z.geometry.type === "Polygon" ? [(c as Ring[])[0]] : (c as Ring[][]).map((poly) => poly[0]);
};

/** A zone outline as a small picture. Decoration with a text label next to it, so it needs no colour to be understood. */
function Outline({ zone }: { zone: ZoneRow }) {
  const rings = outer(zone).filter(Boolean);
  const all = rings.flat();
  const xs = all.map((p) => p[0]);
  const ys = all.map((p) => p[1]);
  const minX = Math.min(...xs);
  const maxY = Math.max(...ys);
  const span = Math.max(Math.max(...xs) - minX, maxY - Math.min(...ys)) || 1;
  const k = 80 / span;
  const d = rings.map((r) => r.map(([x, y], i) => `${i === 0 ? "M" : "L"}${(10 + (x - minX) * k).toFixed(1)} ${(10 + (maxY - y) * k).toFixed(1)}`).join(" ") + " Z").join(" ");
  return (
    <svg viewBox="0 0 100 100" aria-hidden="true" className="size-20 shrink-0">
      <rect width={100} height={100} rx={10} className="fill-navy-950" />
      <path d={d} className="fill-glass-fill-strong stroke-forest-line" strokeWidth={1.5} />
    </svg>
  );
}

/** Zones: the restricted areas (flood plain, river buffer, ...) the zone check compares every plot against. */
export default function Zones() {
  const state = useFetch((signal) => getZones(signal), []);
  return (
    <section>
      <PageHeader eyebrow="OFFICER WORK DESK" title="Restricted" emphasis="zones" subtitle="Land where building is limited. A plot with more than a fifth of its area inside a zone gets 30 points." />
      <div className="mt-8 grid gap-6 lg:grid-cols-[1fr_1.4fr]">
        <Async
          state={state}
          what="the zones"
          isEmpty={(rows) => rows.length === 0}
          empty={{ icon: MapPinOff, title: "No zones", description: "There are no restricted zones in this demo data." }}
        >
          {(rows) => {
            const byType = new Map<string, number>();
            rows.forEach((z) => byType.set(z.zone_type, (byType.get(z.zone_type) ?? 0) + z.plots_touching));
            return (
              <>
                <GlassCard>
                  <h2 className="font-serif text-26 text-cream">Plots touching a zone</h2>
                  <p className="mt-1 text-13 text-muted-on-navy">By kind of zone. Touching is not the same as a clash: a clash needs more than a fifth of the plot inside.</p>
                  <BarList className="mt-4" items={[...byType].map(([type, value]) => ({ label: prettyType(type), value, barClass: "bg-cream" }))} />
                </GlassCard>
                <GlassCard>
                  <h2 className="font-serif text-26 text-cream">
                    {rows.length} {rows.length === 1 ? "zone" : "zones"}
                  </h2>
                  <ul aria-label="Restricted zones" className="mt-4 divide-y divide-glass-border">
                    {rows.map((z) => (
                      <li key={z.id} className="flex items-center gap-4 py-3">
                        <Outline zone={z} />
                        <div className="min-w-0 flex-1">
                          <p className="text-16 text-cream">{prettyType(z.zone_type)}</p>
                          <p className="text-13 text-muted-on-navy">
                            {sqm(z.area_sqm)} · {z.plots_touching} {z.plots_touching === 1 ? "plot touches" : "plots touch"} it
                          </p>
                        </div>
                      </li>
                    ))}
                  </ul>
                </GlassCard>
              </>
            );
          }}
        </Async>
      </div>
    </section>
  );
}
