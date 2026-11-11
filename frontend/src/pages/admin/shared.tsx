import { CircleCheck, CircleOff, CircleSlash, type LucideIcon } from "lucide-react";
import { GlassCard } from "../../components/ui";
import type { PartStatus } from "../../types";

const WORDS: Record<PartStatus["state"], { icon: LucideIcon; word: string; tone: string }> = {
  ok: { icon: CircleCheck, word: "Running", tone: "text-risk-green-tint" },
  off: { icon: CircleOff, word: "Switched off", tone: "text-muted-on-navy" },
  not_loaded: { icon: CircleSlash, word: "Not loaded", tone: "text-muted-on-navy" },
};

/** One part of the system: its name, an icon plus a word for its state (never colour alone) and a sentence of detail. */
export function StatusTile({ name, status, index = 0, wordOverride }: { name: string; status: PartStatus; index?: number; wordOverride?: Partial<Record<PartStatus["state"], string>> }) {
  const s = WORDS[status.state];
  return (
    <GlassCard padding="sm" lift className="rise h-full" style={{ ["--i" as string]: index }}>
      <p className="font-mono text-11 tracking-widest text-muted-on-navy">{name.toUpperCase()}</p>
      <p className={`mt-2 flex items-center gap-2 font-serif text-26 ${s.tone}`}>
        <s.icon className="size-6" aria-hidden="true" />
        {wordOverride?.[status.state] ?? s.word}
      </p>
      <p className="mt-2 text-13 text-muted-on-navy">{status.detail}</p>
    </GlassCard>
  );
}
