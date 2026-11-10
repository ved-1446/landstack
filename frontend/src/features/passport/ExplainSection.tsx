import { Info, Languages, Sparkles } from "lucide-react";
import { useState } from "react";
import { ApiError, explainPassport } from "../../api";
import { Button, Chip } from "../../components/ui";
import { LanguageSelector, useLanguage } from "../guide/language";
import type { StringKey } from "../guide/i18n";
import type { Explanation } from "../../types";

type State = { status: "idle" } | { status: "loading" } | { status: "done"; data: Explanation } | { status: "error"; message: string };

/**
 * "Explain in plain words". The text only rewrites the findings shown above: it never changes a finding, the score or the
 * band. The label always says who wrote it (the AI, or a template written in code when the AI is off). In Hindi or Marathi the
 * AI text is translated from the validated English (and labelled machine-translated); the code-written template stays English.
 */
export function ExplainSection({ ulpin }: { ulpin: string }) {
  const { language, t } = useLanguage();
  const [state, setState] = useState<State>({ status: "idle" });

  async function run() {
    setState({ status: "loading" });
    try {
      setState({ status: "done", data: await explainPassport(ulpin, language) });
    } catch (err) {
      setState({ status: "error", message: err instanceof ApiError ? err.message : t("explain_error") });
    }
  }

  return (
    <section aria-label={t("explain_section")} className="mt-6 border-t border-line-on-cream pt-4" lang={language}>
      {state.status !== "done" && (
        <>
          <LanguageSelector surface="cream" />
          <Button variant="paper" onClick={run} loading={state.status === "loading"} className="mt-3 w-full">
            <Sparkles className="size-4" aria-hidden="true" />
            {state.status === "loading" ? t("explain_writing") : t("explain_button")}
          </Button>
        </>
      )}
      {state.status === "error" && (
        <p role="alert" className="mt-2 text-13 text-ink" lang="en">
          {state.message}
        </p>
      )}

      {state.status === "done" && <Result data={state.data} onAgain={run} />}
    </section>
  );
}

function Result({ data, onAgain }: { data: Explanation; onAgain: () => void }) {
  const { language, t } = useLanguage();
  const lines = data.text.split("\n").filter((line) => line.trim());
  const bullets = lines.filter((l) => l.startsWith("- "));
  const paragraphs = lines.filter((l) => !l.startsWith("- "));
  // the language the explanation text is really in (English when it could not be translated)
  const textLang = data.translation === "machine" && data.language ? data.language : "en";
  const note = data.translation_note ? t(`note_${data.translation_note}` as StringKey) : null;
  // for English the API's own sentence says why the AI was not used; for Hindi/Marathi the note above says it, in that language
  const notice = language === "en" ? data.notice : null;
  return (
    <div className="rounded-card border border-line-on-cream p-3">
      <div className="flex flex-wrap items-center gap-2">
        <Chip surface="cream">{data.source === "ai" ? t("chip_ai") : t("chip_code")}</Chip>
        <h3 className="text-13 font-semibold text-ink">{data.source === "ai" ? t("label_ai") : t("label_template")}</h3>
      </div>
      {data.translation === "machine" && (
        <p className="mt-2 flex items-start gap-2 text-12 text-muted-on-cream">
          <Languages className="mt-0.5 size-3 shrink-0" aria-hidden="true" />
          {t("machine_translated")}
        </p>
      )}
      {(note || notice) && (
        <p className="mt-2 flex items-start gap-2 text-12 text-muted-on-cream">
          <Info className="mt-0.5 size-3 shrink-0" aria-hidden="true" />
          {note ?? notice}
        </p>
      )}
      <div className="mt-3 space-y-2 text-13 text-ink" lang={textLang}>
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
        {data.source === "ai" ? `${t("explain_ai_wrong")} ` : ""}
        {t("explain_unchanged")}
      </p>
      <Button variant="paper" size="sm" className="mt-3" onClick={onAgain}>
        {t("explain_again")}
      </Button>
    </div>
  );
}
