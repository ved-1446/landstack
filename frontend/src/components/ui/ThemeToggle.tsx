import { Moon, Sun } from "lucide-react";
import { useTheme } from "../../lib/theme";
import { cn } from "../../lib/cn";

/** A sun/moon button: switches the whole app between the dark and the light theme and remembers the choice. */
export function ThemeToggle({ className }: { className?: string }) {
  const { theme, toggle } = useTheme();
  const toLight = theme === "dark";
  const Icon = toLight ? Sun : Moon;
  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={toLight ? "Switch to light theme" : "Switch to dark theme"}
      title={toLight ? "Light theme" : "Dark theme"}
      className={cn("inline-flex size-10 shrink-0 items-center justify-center rounded-pill text-muted-on-navy transition-colors duration-150 ease-out hover:bg-glass-fill-strong hover:text-cream", className)}
    >
      <Icon className="size-5" aria-hidden="true" />
    </button>
  );
}
