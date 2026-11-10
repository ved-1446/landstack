import { Button, Popover } from "../../components/ui";
import { prettyType } from "../../constants";
import { cn } from "../../lib/cn";
import type { ConflictType, ConflictTypeInfo, Summary } from "../../types";

export interface MapFilters {
  village: string; // "" = all villages
  conflictType: ConflictType | ""; // "" = all conflict types
}

interface FiltersPopoverProps {
  open: boolean;
  onClose: () => void;
  filters: MapFilters;
  onFilters: (next: MapFilters) => void;
  villages: string[];
  conflictTypes: ConflictTypeInfo[] | null;
  /** findings per conflict type (officers and admins only; null for citizens) */
  summary: Summary | null;
}

/** Village and conflict-type filters. Officers and admins also see how many findings each conflict type has. */
export function FiltersPopover({ open, onClose, filters, onFilters, villages, conflictTypes, summary }: FiltersPopoverProps) {
  const active = filters.village !== "" || filters.conflictType !== "";
  const row = (value: ConflictType | "", label: string, count?: number) => {
    const selected = filters.conflictType === value;
    return (
      <li key={value || "all"}>
        <button
          type="button"
          aria-pressed={selected}
          onClick={() => onFilters({ ...filters, conflictType: value })}
          className={cn(
            "flex w-full items-center justify-between gap-2 rounded-control border px-3 py-2 text-left text-13 transition-colors duration-150 ease-out",
            selected ? "border-cream bg-navy-800 text-cream" : "border-transparent text-muted-on-navy hover:bg-navy-800 hover:text-cream",
          )}
        >
          <span>{label}</span>
          {count !== undefined && <span className="font-mono text-12">{count}</span>}
        </button>
      </li>
    );
  };

  return (
    <Popover open={open} onClose={onClose} title="Filters">
      <label htmlFor="village-filter" className="mb-2 mt-3 block font-mono text-11 tracking-wider text-faint-on-navy">
        VILLAGE
      </label>
      <select
        id="village-filter"
        value={filters.village}
        onChange={(e) => onFilters({ ...filters, village: e.target.value })}
        className="h-11 w-full rounded-control border border-line-on-navy bg-navy-950 px-3 text-14 text-cream"
      >
        <option value="">All villages</option>
        {villages.map((village) => (
          <option key={village} value={village}>
            {village}
          </option>
        ))}
      </select>

      <h3 className="mb-2 mt-4 font-mono text-11 tracking-wider text-faint-on-navy">CONFLICT TYPE{summary ? " · FINDINGS" : ""}</h3>
      <ul className="space-y-1">
        {row("", "All conflict types")}
        {(conflictTypes ?? []).map((info) =>
          row(info.type, info.simulated ? `${prettyType(info.type)} (simulated)` : prettyType(info.type), summary?.findings_per_type[info.type]),
        )}
      </ul>

      {active && (
        <Button variant="secondary" size="sm" className="mt-4" onClick={() => onFilters({ village: "", conflictType: "" })}>
          Clear filters
        </Button>
      )}
    </Popover>
  );
}
