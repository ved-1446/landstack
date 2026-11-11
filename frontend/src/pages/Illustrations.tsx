import type { Step } from "./content";

// Four small original illustrations, one per step. Inline SVG, drawn with token colours only; decoration, so hidden from screen readers.
const base = "size-full";

function MapShapes() {
  return (
    <svg viewBox="0 0 120 90" className={base} fill="none" aria-hidden="true">
      <rect x="6" y="6" width="108" height="78" rx="10" className="stroke-faint-on-navy" strokeWidth="1.5" strokeDasharray="4 4" />
      <path d="M22 60 L22 30 L52 24 L58 58 Z" className="fill-glass-fill-strong stroke-forest-line" strokeWidth="2" />
      <path d="M64 56 L68 26 L98 34 L94 62 Z" className="fill-glass-fill-strong stroke-forest-line" strokeWidth="2" />
      <circle cx="40" cy="42" r="3.5" className="fill-coral" />
      <circle cx="82" cy="46" r="3.5" className="fill-coral" />
    </svg>
  );
}

function Compare() {
  return (
    <svg viewBox="0 0 120 90" className={base} fill="none" aria-hidden="true">
      <rect x="8" y="14" width="46" height="62" rx="6" className="fill-glass-fill-strong stroke-faint-on-navy" strokeWidth="1.5" />
      <path d="M16 30 H46 M16 42 H46 M16 54 H36" className="stroke-muted-on-navy" strokeWidth="2.5" strokeLinecap="round" />
      <rect x="66" y="14" width="46" height="62" rx="6" className="fill-glass-fill-strong stroke-faint-on-navy" strokeWidth="1.5" />
      <path d="M74 36 L90 24 L104 36 V62 H74 Z" className="stroke-forest-line" strokeWidth="2" />
      <path d="M56 45 H64 M60 41 L64 45 L60 49" className="stroke-coral" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function Count() {
  return (
    <svg viewBox="0 0 120 90" className={base} fill="none" aria-hidden="true">
      <rect x="10" y="52" width="20" height="26" rx="4" className="fill-glass-fill-strong stroke-faint-on-navy" strokeWidth="1.5" />
      <rect x="40" y="36" width="20" height="42" rx="4" className="fill-glass-fill-strong stroke-faint-on-navy" strokeWidth="1.5" />
      <rect x="70" y="18" width="20" height="60" rx="4" className="fill-coral" />
      <path d="M98 70 V22 M94 28 L98 22 L102 28" className="stroke-muted-on-navy" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function Passport() {
  return (
    <svg viewBox="0 0 120 90" className={base} fill="none" aria-hidden="true">
      <rect x="26" y="8" width="68" height="74" rx="8" className="fill-paper" />
      <path d="M36 24 H72 M36 34 H84 M36 44 H64" className="stroke-muted-on-cream" strokeWidth="3" strokeLinecap="round" />
      <rect x="68" y="56" width="18" height="18" rx="3" className="stroke-ink" strokeWidth="2" />
      <path d="M72 62 H76 V66 M82 62 V70 M72 70 H78" className="stroke-ink" strokeWidth="2" strokeLinecap="round" />
      <circle cx="42" cy="64" r="9" className="fill-risk-green" />
      <path d="M37.5 64 L41 67.5 L47 60.5" className="stroke-ink" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

const ART = { map: MapShapes, compare: Compare, count: Count, passport: Passport } as const;

export function StepArt({ step, className }: { step: Step["key"]; className?: string }) {
  const Art = ART[step];
  return (
    <div className={className ?? "h-24 w-32"}>
      <Art />
    </div>
  );
}
