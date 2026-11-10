import { ArrowRight, LoaderCircle } from "lucide-react";
import { forwardRef, useState, type FormEvent } from "react";
import { cn } from "../../lib/cn";

interface SearchPillProps {
  /** Runs the search. Returns an error message to show, or null when it worked. */
  onSearch: (ulpin: string) => Promise<string | null>;
  className?: string;
}

const ULPIN_SHAPE = /^[A-Z0-9]{14}$/;

/** The ULPIN search box: a glass pill with a mono input and a coral arrow button. */
export const SearchPill = forwardRef<HTMLInputElement, SearchPillProps>(function SearchPill({ onSearch, className }, ref) {
  const [value, setValue] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    const ulpin = value.trim().toUpperCase();
    if (!ULPIN_SHAPE.test(ulpin)) {
      setError("A ULPIN is 14 letters and digits, like MH000100000001.");
      return;
    }
    setBusy(true);
    setError(null);
    setError(await onSearch(ulpin));
    setBusy(false);
  }

  return (
    <form onSubmit={submit} role="search" className={cn("flex flex-col gap-2", className)}>
      <div className="glass flex h-12 items-center gap-2 rounded-pill pl-4 pr-1 shadow-2">
        <label htmlFor="ulpin-search" className="sr-only">
          Search by ULPIN
        </label>
        <input
          id="ulpin-search"
          ref={ref}
          value={value}
          onChange={(e) => {
            setValue(e.target.value);
            setError(null);
          }}
          placeholder="Search by ULPIN"
          autoComplete="off"
          spellCheck={false}
          maxLength={14}
          aria-invalid={error ? true : undefined}
          aria-describedby={error ? "ulpin-search-error" : undefined}
          className="min-w-0 flex-1 bg-transparent font-mono text-14 uppercase tracking-wider text-cream placeholder:normal-case placeholder:tracking-normal placeholder:text-faint-on-navy focus:outline-none"
        />
        <button
          type="submit"
          aria-label="Search"
          disabled={busy}
          className="flex size-10 shrink-0 items-center justify-center rounded-pill bg-coral text-navy-950 transition-colors duration-150 ease-out hover:bg-coral-hover active:bg-coral-pressed disabled:opacity-60"
        >
          {busy ? <LoaderCircle className="size-4 animate-spin motion-reduce:animate-none" aria-hidden="true" /> : <ArrowRight className="size-4" aria-hidden="true" />}
        </button>
      </div>
      {error && (
        <p id="ulpin-search-error" role="alert" className="glass rounded-control px-3 py-2 text-12 text-cream">
          {error}
        </p>
      )}
    </form>
  );
});
