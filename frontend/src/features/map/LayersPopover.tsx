import { Popover, Segmented, Switch, type SegmentedOption } from "../../components/ui";
import { cn } from "../../lib/cn";
import { BASEMAPS, BASEMAP_ORDER, type BasemapId } from "./basemaps";
import type { MapLayerSwitches } from "./MapView";

interface LayersPopoverProps {
  open: boolean;
  onClose: () => void;
  basemap: BasemapId;
  onBasemap: (id: BasemapId) => void;
  layers: MapLayerSwitches;
  onLayers: (next: MapLayerSwitches) => void;
}

/** A tiny drawn picture of each basemap (no images are loaded, so it works offline). */
function Thumb({ id }: { id: BasemapId }) {
  const sky = { light: "bg-cream", dark: "bg-navy-950", satellite: "bg-navy-800" }[id];
  const line = { light: "bg-faint-on-cream", dark: "bg-faint-on-navy", satellite: "bg-mist" }[id];
  return (
    <span aria-hidden="true" className={cn("relative block h-12 overflow-hidden rounded-control border border-line-on-navy", sky)}>
      <span className={cn("absolute left-2 top-0 h-full w-px", line)} />
      <span className={cn("absolute left-0 top-4 h-px w-full", line)} />
      <span className={cn("absolute bottom-3 right-3 size-4 rounded-control opacity-60", line)} />
      {id === "satellite" && <span className="absolute inset-x-0 bottom-0 h-4 bg-risk-green-ink opacity-50" />}
    </span>
  );
}

export function LayersPopover({ open, onClose, basemap, onBasemap, layers, onLayers }: LayersPopoverProps) {
  const options: SegmentedOption<BasemapId>[] = BASEMAP_ORDER.map((id) => ({
    value: id,
    label: BASEMAPS[id].label,
    preview: <Thumb id={id} />,
  }));
  return (
    <Popover open={open} onClose={onClose} title="Map layers">
      <h3 className="mb-2 mt-3 font-mono text-11 tracking-wider text-faint-on-navy">BASEMAP</h3>
      <Segmented label="Basemap" value={basemap} onChange={onBasemap} options={options} />

      <h3 className="mb-1 mt-4 font-mono text-11 tracking-wider text-faint-on-navy">LAYERS</h3>
      <Switch label="Parcel boundaries" checked={layers.boundaries} onCheckedChange={(boundaries) => onLayers({ ...layers, boundaries })} />
      <Switch
        label="ULPIN labels"
        description="Zoom 16 and closer"
        checked={layers.labels}
        onCheckedChange={(labels) => onLayers({ ...layers, labels })}
      />
      <Switch
        label="Risk colours"
        description="Green, amber, red"
        checked={layers.risk}
        onCheckedChange={(risk) => onLayers({ ...layers, risk })}
      />
      <Switch label="Restricted zones" description="Not available yet: the API has no zones data" checked={false} disabled onCheckedChange={() => undefined} />
      <Switch
        label="Unrecorded construction (simulated)"
        description="New buildings between two generated snapshots, T0 and T1. Not real imagery."
        checked={layers.construction}
        onCheckedChange={(construction) => onLayers({ ...layers, construction })}
      />

      <p className="mt-4 border-t border-line-on-navy pt-3 text-11 text-faint-on-navy">Map data: {BASEMAPS[basemap].credit}</p>
    </Popover>
  );
}
