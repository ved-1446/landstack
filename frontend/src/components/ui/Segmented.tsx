import { Check } from "lucide-react";
import type { KeyboardEvent, ReactNode } from "react";
import { cn } from "../../lib/cn";

export interface SegmentedOption<T extends string> {
  value: T;
  label: string;
  /** a small picture of the option (for example a basemap thumbnail) */
  preview?: ReactNode;
}

interface SegmentedProps<T extends string> {
  value: T;
  onChange: (value: T) => void;
  options: SegmentedOption<T>[];
  label: string;
}

/** A one-of-many choice, built as a radio group (arrow keys move between options). The chosen one gets a cream ring. */
export function Segmented<T extends string>({ value, onChange, options, label }: SegmentedProps<T>) {
  function onKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    const step = event.key === "ArrowRight" || event.key === "ArrowDown" ? 1 : event.key === "ArrowLeft" || event.key === "ArrowUp" ? -1 : 0;
    if (!step) return;
    event.preventDefault();
    const index = options.findIndex((o) => o.value === value);
    onChange(options[(index + step + options.length) % options.length].value);
  }

  return (
    <div role="radiogroup" aria-label={label} onKeyDown={onKeyDown} className="grid grid-cols-3 gap-2">
      {options.map((option) => {
        const selected = option.value === value;
        return (
          <button
            key={option.value}
            type="button"
            role="radio"
            aria-checked={selected}
            tabIndex={selected ? 0 : -1}
            onClick={() => onChange(option.value)}
            className={cn(
              "relative flex flex-col gap-2 rounded-card border p-2 text-left text-12 transition-colors duration-150 ease-out",
              selected ? "border-cream bg-navy-800 text-cream" : "border-line-on-navy text-muted-on-navy hover:bg-navy-800",
            )}
          >
            {option.preview}
            <span className="flex items-center justify-between">
              {option.label}
              {selected && <Check className="size-4" aria-hidden="true" />}
            </span>
          </button>
        );
      })}
    </div>
  );
}
