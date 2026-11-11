import type { CSSProperties, ReactNode } from "react";
import { cn } from "../../lib/cn";

interface PageHeaderProps {
  /** small uppercase mono label above the title, for example "OFFICER WORK DESK" */
  eyebrow: string;
  /** the plain start of the title */
  title: string;
  /** ONE word (or short phrase) in italic coral at the end of the title */
  emphasis?: string;
  subtitle?: ReactNode;
  actions?: ReactNode;
  className?: string;
  /** the level of the heading: 1 for the page title */
  as?: "h1" | "h2";
}

const step = (n: number) => ({ ["--i" as string]: n }) as CSSProperties;

/** Eyebrow + serif title with one italic coral word + subtitle. The same on every page. */
export function PageHeader({ eyebrow, title, emphasis, subtitle, actions, className, as: Heading = "h1" }: PageHeaderProps) {
  return (
    <header className={cn("flex flex-wrap items-end justify-between gap-4", className)}>
      <div className="min-w-0">
        <p className="rise font-mono text-12 tracking-widest text-muted-on-navy" style={step(0)}>
          {eyebrow}
        </p>
        <Heading className="rise mt-2 font-serif text-34 text-cream md:text-58" style={step(1)}>
          {title}
          {emphasis && (
            <>
              {" "}
              <em className="text-coral-text">{emphasis}</em>
            </>
          )}
        </Heading>
        {subtitle && (
          <p className="rise mt-3 max-w-2xl text-16 text-muted-on-navy" style={step(2)}>
            {subtitle}
          </p>
        )}
      </div>
      {actions && <div className="flex items-center gap-3">{actions}</div>}
    </header>
  );
}
