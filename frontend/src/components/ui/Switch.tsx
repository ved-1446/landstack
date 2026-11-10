import { useId } from "react";
import { cn } from "../../lib/cn";

interface SwitchProps {
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
  label: string;
  description?: string;
  disabled?: boolean;
}

/** An on/off switch. On = cream track (coral is reserved for primary actions, never for toggles). */
export function Switch({ checked, onCheckedChange, label, description, disabled = false }: SwitchProps) {
  const id = useId();
  return (
    <div className="flex items-center justify-between gap-4 py-2">
      <div className="min-w-0">
        <label htmlFor={id} className={cn("block text-14 text-cream", disabled && "opacity-60")}>
          {label}
        </label>
        {description && <p className="text-12 text-faint-on-navy">{description}</p>}
      </div>
      <button
        id={id}
        type="button"
        role="switch"
        aria-checked={checked}
        disabled={disabled}
        onClick={() => onCheckedChange(!checked)}
        className={cn(
          "relative h-6 w-10 shrink-0 rounded-pill border transition-colors duration-150 ease-out disabled:opacity-60",
          checked ? "border-cream bg-cream" : "border-line-on-navy bg-navy-800",
        )}
      >
        <span
          aria-hidden="true"
          className={cn(
            "absolute top-1/2 size-4 -translate-y-1/2 rounded-pill transition-all duration-150 ease-out",
            checked ? "left-5 bg-navy-950" : "left-1 bg-muted-on-navy",
          )}
        />
      </button>
    </div>
  );
}
