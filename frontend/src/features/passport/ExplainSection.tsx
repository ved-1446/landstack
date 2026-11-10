import { Info, Sparkles } from "lucide-react";
import { useState } from "react";
import { ApiError, explainPassport } from "../../api";
import { Button, Chip } from "../../components/ui";
import type { Explanation } from "../../types";

type State = { status: "idle" } | { status: "loading" } | { status: "done"; data: Explanation } | { status: "error"; message: string };

/**
 * "Explain in plain words". The text only rewrites the findings shown above: it never changes a finding, the score or the
 * band. The label under the heading always says who wrote it (the AI, or a template written in code when the AI is off).
 */
export function ExplainSection({ ulpin }: { ulpin: string }) {
  const [state, setState] = useState<State>({ status: "idle" });

  async function run() {
    setState({ status: "loading" });
    try {
      setState({ status: "done", data: await explainPassport(ulpin) });
    } catch (err) {
      setState({ status: "error", message: err instanceof ApiError ? err.message : "The explanation could not be made. Please try again." });
    }
  }

  return (
    <section aria-label="Plain-words explanation" className="mt-6 border-t border-line-on-cream pt-4">
      {state.status !== "done" && (
        <Button variant="paper" onClick={run} loading={state.status === "loading"} className="w-full">
          <Sparkles className="size-4" aria-hidden="true" />
          {state.status === "loading" ? "Writing…" : "Explain in plain words"}
        </Button>
      )}
      {state.status === "error" && (
        <p role="alert" className="mt-2 text-13 text-ink">
          {state.message}
        </p>
      )}

      {state.status === "done" && <Result data={state.data} onAgain={run} />}
    </section>
  );
}

function Result({ data, onAgain }: { data: Explanation; onAgain: () => void }) {
  const lines = data.text.split("\n").filter((line) => line.trim());
  const bullets = lines.filter((l) => l.startsWith("- "));
  const paragraphs = lines.filter((l) => !l.startsWith("- "));
  return (
    <div className="rounded-card border border-line-on-cream p-3">
      <div className="flex flex-wrap items-center gap-2">
        <Chip surface="cream">{data.source === "ai" ? "AI" : "Written by code"}</Chip>
        <h3 className="text-13 font-semibold text-ink">{data.label}</h3>
      </div>
      {data.notice && (
        <p className="mt-2 flex items-start gap-2 text-12 text-muted-on-cream">
          <Info className="mt-0.5 size-3 shrink-0" aria-hidden="true" />
          {data.notice}
        </p>
      )}
      <div className="mt-3 space-y-2 text-13 text-ink">
        {paragraphs.slice(0, 2).map((p) => (
          <p key={p}>{p}</p>
        ))}
        {bullets.length > 0 && (
          <ul className="list-disc space-y-2 pl-4">
            {bullets.map((b) => (
              <li key={b}>{b.slice(2)}</li>
            ))}
          </ul>
        )}
        {paragraphs.slice(2).map((p) => (
          <p key={p}>{p}</p>
        ))}
      </div>
      <p className="mt-3 text-12 text-muted-on-cream">
        {data.source === "ai" ? "AI can be wrong. " : ""}The score, band and findings above are not changed by this summary.
      </p>
      <Button variant="paper" size="sm" className="mt-3" onClick={onAgain}>
        Explain again
      </Button>
    </div>
  );
}
