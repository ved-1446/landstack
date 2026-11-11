import { useMemo } from "react";
import type { Band, PlotFeature } from "../types";

const FILL: Record<Band, string> = { green: "fill-risk-green", amber: "fill-risk-amber", red: "fill-risk-red" };
const RING: Record<Band, string> = { green: "stroke-risk-green", amber: "stroke-risk-amber", red: "stroke-risk-red" };
const SIZE = 300;

type Ring = number[][];
const ringOf = (f: PlotFeature): Ring => (f.geometry.coordinates[0] ?? []) as Ring;

/**
 * A tiny map preview: every plot outline filled with its band colour. It is only a picture (no pan or zoom, no basemap), so the
 * counts are always written next to it. The real map is one click away.
 */
export function MiniMap({ features, className, markers = false }: { features: PlotFeature[]; className?: string; markers?: boolean }) {
  const { paths, counts } = useMemo(() => {
    const coords = features.flatMap(ringOf);
    if (coords.length === 0) return { paths: [] as { d: string; band: Band; key: string; x: number; y: number }[], counts: { green: 0, amber: 0, red: 0 } };
    const lons = coords.map((c) => c[0]);
    const lats = coords.map((c) => c[1]);
    const minX = Math.min(...lons);
    const maxY = Math.max(...lats);
    const span = Math.max(Math.max(...lons) - minX, maxY - Math.min(...lats)) || 1;
    const k = (SIZE - 20) / span;
    const counts: Record<Band, number> = { green: 0, amber: 0, red: 0 };
    const paths = features.map((f) => {
      const ring = ringOf(f);
      const cx = ring.reduce((sum, c) => sum + c[0], 0) / (ring.length || 1);
      const cy = ring.reduce((sum, c) => sum + c[1], 0) / (ring.length || 1);
      counts[f.properties.band] += 1;
      const d = ringOf(f).map(([x, y], i) => `${i === 0 ? "M" : "L"}${(10 + (x - minX) * k).toFixed(1)} ${(10 + (maxY - y) * k).toFixed(1)}`).join(" ") + " Z";
      return { d, band: f.properties.band, key: f.properties.ulpin, x: 10 + (cx - minX) * k, y: 10 + (maxY - cy) * k };
    });
    return { paths, counts };
  }, [features]);

  return (
    <svg viewBox={`0 0 ${SIZE} ${SIZE}`} role="img" className={className ?? "size-full"} aria-label={`Map preview: ${counts.green} green, ${counts.amber} amber and ${counts.red} red plots`}>
      <rect width={SIZE} height={SIZE} rx={12} className="fill-navy-950" />
      {paths.map((p) => (
        <path key={p.key} d={p.d} className={`${FILL[p.band]} stroke-navy-950`} fillOpacity={0.85} strokeWidth={0.6} />
      ))}
      {/* few, far-apart plots would be specks: ring each one so it can be found (the band is also written in the label above) */}
      {markers && paths.map((p) => <circle key={`m-${p.key}`} cx={p.x} cy={p.y} r={14} fill="none" strokeWidth={3} className={RING[p.band]} />)}
    </svg>
  );
}
