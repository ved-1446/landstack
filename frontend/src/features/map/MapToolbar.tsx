import { FileText, Layers, LayoutGrid, SlidersHorizontal, type LucideIcon } from "lucide-react";
import { cn } from "../../lib/cn";

export type PanelId = "layers" | "filters" | "plots";

interface MapToolbarProps {
  /** officers and admins see "Passports"; citizens see "My plots" */
  staff: boolean;
  active: PanelId | null;
  onToggle: (id: PanelId) => void;
}

/** The three map tools as a row of glass pills under the search box (this replaces the old side rail). */
export function MapToolbar({ staff, active, onToggle }: MapToolbarProps) {
  const items: { id: PanelId; label: string; icon: LucideIcon }[] = [
    { id: "layers", label: "Layers", icon: Layers },
    { id: "filters", label: "Filters", icon: SlidersHorizontal },
    staff ? { id: "plots", label: "Passports", icon: FileText } : { id: "plots", label: "My plots", icon: LayoutGrid },
  ];
  return (
    <div data-rail role="toolbar" aria-label="Map tools" className="flex flex-wrap gap-2">
      {items.map((item) => (
        <button
          key={item.id}
          type="button"
          aria-pressed={active === item.id}
          onClick={() => onToggle(item.id)}
          className={cn(
            "glass inline-flex h-10 items-center gap-2 rounded-pill px-4 text-13 transition-colors duration-150 ease-out hover:bg-glass-fill-strong",
            active === item.id ? "border-coral text-cream" : "text-muted-on-navy",
          )}
        >
          <item.icon className="size-4" aria-hidden="true" />
          {item.label}
        </button>
      ))}
    </div>
  );
}
