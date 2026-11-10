import { useId } from "react";
import { Chip } from "../../components/ui";
import type { Unusual } from "../../types";

/**
 * A quiet "Unusual" chip. It is a statistical hint from the Phase 9 model, never a conflict: it adds no points and
 * does not change the band. The tooltip says so in plain words and lists the reasons. It opens on hover AND on
 * keyboard focus, so it is not mouse-only.
 */
export function UnusualChip({ unusual }: { unusual: Unusual }) {
  const tipId = useId();
  return (
    <span className="group relative inline-flex rounded-pill" tabIndex={0} aria-describedby={tipId}>
      <Chip surface="cream" tone="ml">
        Unusual
      </Chip>
      <span
        id={tipId}
        role="tooltip"
        className="pointer-events-none absolute left-1/2 top-full z-panel mt-2 w-72 -translate-x-1/2 rounded-control bg-navy-950 p-3 text-left text-12 text-cream opacity-0 shadow-2 transition-opacity duration-150 ease-out group-hover:opacity-100 group-focus:opacity-100"
      >
        <span className="block">Unusual compared with other plots. This is not a conflict and adds no points.</span>
        {unusual.reasons.length > 0 && (
          <ul className="mt-2 list-disc space-y-1 pl-4 text-muted-on-navy">
            {unusual.reasons.map((reason) => (
              <li key={reason}>{reason}</li>
            ))}
          </ul>
        )}
      </span>
    </span>
  );
}
