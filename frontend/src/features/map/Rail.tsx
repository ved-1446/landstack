import { FileText, Layers, LayoutGrid, Search, SlidersHorizontal, User, type LucideIcon } from "lucide-react";
import { cn } from "../../lib/cn";

export type PanelId = "layers" | "filters" | "plots" | "account";

interface RailProps {
  /** officers and admins see "Passports"; citizens see "My plots" */
  staff: boolean;
  active: PanelId | null;
  onToggle: (id: PanelId) => void;
  onSearch: () => void;
}

interface Item {
  key: string;
  label: string;
  icon: LucideIcon;
  panel?: PanelId;
  bottom?: boolean;
}

/**
 * The 68px icon rail on the left. Under 768px it becomes a bottom tab bar (icons with small labels).
 * The active icon is coral.
 */
export function Rail({ staff, active, onToggle, onSearch }: RailProps) {
  const items: Item[] = [
    { key: "layers", label: "Map layers", icon: Layers, panel: "layers" },
    { key: "search", label: "Search", icon: Search },
    { key: "filters", label: "Filters", icon: SlidersHorizontal, panel: "filters" },
    staff
      ? { key: "plots", label: "Passports", icon: FileText, panel: "plots" }
      : { key: "plots", label: "My plots", icon: LayoutGrid, panel: "plots" },
    { key: "account", label: "Account", icon: User, panel: "account", bottom: true },
  ];

  return (
    <nav
      data-rail
      aria-label="Map tools"
      className="fixed z-rail flex border-line-on-navy bg-navy-900 md:inset-y-0 md:left-0 md:w-(--rail-width) md:flex-col md:items-center md:gap-2 md:border-r md:py-4 max-md:inset-x-0 max-md:bottom-0 max-md:h-(--tabbar-height) max-md:border-t"
    >
      <span aria-hidden="true" className="mb-4 hidden size-11 items-center justify-center rounded-control bg-navy-800 font-serif text-26 text-cream md:flex">
        L
      </span>
      {items.map((item) => {
        const pressed = item.panel ? active === item.panel : false;
        return (
          <button
            key={item.key}
            type="button"
            title={item.label}
            aria-label={item.label}
            aria-pressed={item.panel ? pressed : undefined}
            onClick={() => (item.panel ? onToggle(item.panel) : onSearch())}
            className={cn(
              "flex items-center justify-center rounded-control transition-colors duration-150 ease-out hover:bg-navy-800 hover:text-cream md:size-11 max-md:h-full max-md:flex-1 max-md:flex-col max-md:gap-1",
              pressed ? "bg-navy-800 text-coral" : "text-muted-on-navy",
              item.bottom && "md:mt-auto",
            )}
          >
            <item.icon className="size-5" aria-hidden="true" />
            <span className="text-11 md:sr-only">{item.label}</span>
          </button>
        );
      })}
    </nav>
  );
}
