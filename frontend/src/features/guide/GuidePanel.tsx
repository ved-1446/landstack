import { AlertTriangle, CircleHelp, Clock, ExternalLink, Info, Languages, PowerOff, SendHorizontal, Sparkles, X } from "lucide-react";
import { useCallback, useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { Link } from "react-router";
import { askGuide } from "../../api";
import { Button, Chip, GlassCard } from "../../components/ui";
import type { GuideAnswer, GuideStatus } from "../../types";
import type { StringKey } from "./i18n";
import { LanguageSelector, useLanguage } from "./language";

const MAX_QUESTION = 500; // the same limit the API enforces
const SUGGESTIONS: StringKey[] = ["suggestion_1", "suggestion_2", "suggestion_3"];

type Message =
  | { id: number; kind: "user"; text: string; lang: string }
  | { id: number; kind: "answer"; question: string; answer: GuideAnswer }
  | { id: number; kind: "error"; question: string; text: string };

// Every state is written in words with an icon, never shown by colour alone.
const STATUS: Record<GuideStatus, { icon: typeof Sparkles; label: StringKey }> = {
  answered: { icon: Sparkles, label: "status_answered" },
  no_sources: { icon: CircleHelp, label: "status_no_sources" },
  ai_off: { icon: PowerOff, label: "status_ai_off" },
  ai_busy: { icon: Clock, label: "status_ai_busy" },
  ai_failed: { icon: AlertTriangle, label: "status_ai_failed" },
};

interface GuidePanelProps {
  /** "page" renders the conversation as a full page card (the /app/guide route); "popup" is the compact panel of the bottom-right launcher */
  variant?: "popup" | "page";
  /** popup only: whether the panel is showing. The conversation is kept when it is not. */
  open?: boolean;
  onClose?: () => void;
}

/**
 * The Land Guide chat. It stays mounted when the panel is closed, so the conversation is kept until the page is reloaded
 * (it is held in memory only and never stored). Only the question text is sent: no plot, no personal data.
 * The visitor picks English, हिन्दी or मराठी; it is never guessed. Questions in Hindi or Marathi are translated to English on
 * the server, answered from the English sources, and translated back (retrieval is English-only).
 */
export function GuidePanel({ variant = "page", open = true, onClose = () => undefined }: GuidePanelProps) {
  const { language, t } = useLanguage();
  const [messages, setMessages] = useState<Message[]>([]);
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const nextId = useRef(1);
  const abort = useRef<AbortController | null>(null);
  const end = useRef<HTMLDivElement>(null);

  useEffect(() => () => abort.current?.abort(), []);
  // the popup: when it opens (or finishes loading while open), the keyboard focus goes to the question box
  useEffect(() => {
    if (open && variant === "popup") document.getElementById("guide-input")?.focus();
  }, [open, variant]);
  useEffect(() => {
    if (open && variant === "popup") end.current?.scrollIntoView?.({ block: "end" });
  }, [open, messages, loading]);

  const ask = useCallback(
    async (question: string, addUserMessage: boolean) => {
      const clean = question.trim();
      if (!clean) return;
      setMessages((old) => (addUserMessage ? [...old, { id: nextId.current++, kind: "user", text: clean, lang: language }] : old));
      setLoading(true);
      abort.current?.abort();
      const controller = new AbortController();
      abort.current = controller;
      try {
        const answer = await askGuide(clean, language, controller.signal);
        setMessages((old) => [...old, { id: nextId.current++, kind: "answer", question: clean, answer }]);
      } catch (err) {
        if (controller.signal.aborted) return;
        const message = err instanceof Error ? err.message : "Something went wrong.";
        setMessages((old) => [...old, { id: nextId.current++, kind: "error", question: clean, text: message }]);
      }
      setLoading(false);
    },
    [language],
  );

  function retry(question: string, messageId: number) {
    setMessages((old) => old.filter((m) => m.id !== messageId)); // drop the failed reply; the question above it stays
    void ask(question, false);
  }

  function submit(event?: FormEvent) {
    event?.preventDefault();
    if (loading || !text.trim()) return;
    const question = text;
    setText("");
    void ask(question, true);
  }

  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      submit();
    }
  }

  const footer = (
    <form onSubmit={submit} lang={language}>
      <label htmlFor="guide-input" className="sr-only">
        {t("input_label")}
      </label>
      <textarea
        id="guide-input"
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={onKeyDown}
        maxLength={MAX_QUESTION}
        rows={2}
        placeholder={t("input_placeholder")}
        className="w-full resize-none rounded-control border border-line-on-navy bg-navy-950 px-3 py-2 text-14 text-cream placeholder:text-faint-on-navy"
      />
      <div className="mt-2 flex items-center justify-between gap-3">
        <p className="text-11 text-faint-on-navy">{t("guide_footer")}</p>
        <Button type="submit" size="sm" loading={loading} disabled={!text.trim()} aria-label={t("send_question")}>
          <SendHorizontal className="size-4" aria-hidden="true" />
          {t("ask")}
        </Button>
      </div>
    </form>
  );

  const body = (
    <>
      <div className="mt-2">
        <LanguageSelector />
      </div>

      <div className="mt-3 flex items-start gap-2 rounded-card border border-line-on-navy bg-navy-900 p-3" lang={language}>
        <Chip>AI</Chip>
        <p className="text-12 text-muted-on-navy">{t("guide_intro")}</p>
      </div>

      {messages.length === 0 && !loading && (
        <div className="mt-4" lang={language}>
          <p className="mb-2 font-mono text-11 tracking-wider text-faint-on-navy">{t("try_asking")}</p>
          <ul className="flex flex-wrap gap-2">
            {SUGGESTIONS.map((key) => (
              <li key={key}>
                <Chip onClick={() => void ask(t(key), true)}>{t(key)}</Chip>
              </li>
            ))}
          </ul>
        </div>
      )}

      <ol aria-label="Conversation" aria-live="polite" className="mt-4 space-y-3">
        {messages.map((m) =>
          m.kind === "user" ? (
            <li key={m.id} className="ml-8 rounded-card bg-navy-800 p-3">
              <p className="mb-1 font-mono text-11 tracking-wider text-faint-on-navy" lang={language}>
                {t("you")}
              </p>
              <p className="whitespace-pre-wrap text-14 text-cream" lang={m.lang}>
                {m.text}
              </p>
            </li>
          ) : m.kind === "answer" ? (
            <AnswerBubble key={m.id} answer={m.answer} onRetry={() => retry(m.question, m.id)} />
          ) : (
            <li key={m.id} className="mr-8 rounded-card border border-line-on-navy bg-navy-900 p-3">
              <Chip>
                <span className="inline-flex items-center gap-1">
                  <AlertTriangle className="size-3 shrink-0" aria-hidden="true" />
                  <span lang={language}>{t("status_error")}</span>
                </span>
              </Chip>
              <p className="mt-2 text-13 text-cream" lang="en">
                {m.text}
              </p>
              <Button variant="secondary" size="sm" className="mt-3" onClick={() => retry(m.question, m.id)}>
                <span lang={language}>{t("try_again")}</span>
              </Button>
            </li>
          ),
        )}
        {loading && (
          <li role="status" className="mr-8 flex items-center gap-2 rounded-card border border-line-on-navy bg-navy-900 p-3 text-13 text-muted-on-navy" lang={language}>
            <Clock className="size-4" aria-hidden="true" />
            {t("looking")}
          </li>
        )}
      </ol>
      <div ref={end} />
    </>
  );

  if (variant === "page") {
    return (
      <GlassCard padding="none" className="mx-auto flex w-full max-w-3xl flex-col" aria-label={t("guide_title")}>
        <div className="min-h-96 px-6 pb-6 pt-4">{body}</div>
        <div className="sticky bottom-0 rounded-b-glass border-t border-glass-border bg-glass px-6 py-4">{footer}</div>
      </GlassCard>
    );
  }
  return (
    <div
      role="dialog"
      aria-label={t("guide_title")}
      hidden={!open}
      className="glass route-in flex max-h-(--guide-max-height) w-(--guide-popup-width) flex-col overflow-hidden rounded-panel shadow-2"
    >
      <div className="flex shrink-0 items-center justify-between gap-2 px-4 pt-3">
        <h2 className="font-serif text-26 text-cream">{t("guide_title")}</h2>
        <div className="flex items-center gap-1">
          <Link
            to="/app/guide"
            onClick={onClose}
            className="inline-flex h-8 items-center gap-1 rounded-pill px-3 text-13 text-muted-on-navy hover:bg-glass-fill-strong hover:text-cream"
          >
            Open full page
            <ExternalLink className="size-3" aria-hidden="true" />
          </Link>
          <Button variant="ghost" size="icon" aria-label={`Close ${t("guide_title")}`} onClick={onClose}>
            <X className="size-5" aria-hidden="true" />
          </Button>
        </div>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto px-4 pb-4">{body}</div>
      <div className="shrink-0 border-t border-line-on-navy px-4 py-3">{footer}</div>
    </div>
  );
}

function AnswerBubble({ answer, onRetry }: { answer: GuideAnswer; onRetry: () => void }) {
  const { language, t } = useLanguage();
  const status = STATUS[answer.status];
  const retryable = answer.status === "ai_busy" || answer.status === "ai_failed";
  // the language the answer text is really in: translated by the server, or English (a fallback, or an English question)
  const answerLang = answer.language && (answer.translation === "machine" || answer.translation === "fixed") ? answer.language : "en";
  const note = answer.translation_note ? t(`note_${answer.translation_note}` as StringKey) : null;
  return (
    <li className="mr-8 rounded-card border border-line-on-navy bg-navy-900 p-3">
      <Chip>
        <span className="inline-flex items-center gap-1">
          <status.icon className="size-3 shrink-0" aria-hidden="true" />
          <span lang={language}>{t(status.label)}</span>
        </span>
      </Chip>
      <p className="mt-2 whitespace-pre-wrap text-14 text-cream" lang={answerLang}>
        {answer.answer}
      </p>
      {answer.translation === "machine" && (
        <p className="mt-2 flex items-start gap-2 text-12 text-muted-on-navy" lang={language}>
          <Languages className="mt-0.5 size-3 shrink-0" aria-hidden="true" />
          {t("machine_translated")}
        </p>
      )}
      {note && (
        <p className="mt-2 flex items-start gap-2 text-12 text-muted-on-navy" lang={language}>
          <Info className="mt-0.5 size-3 shrink-0" aria-hidden="true" />
          {note}
        </p>
      )}

      {answer.sources.length > 0 && (
        <div className="mt-3" lang={language}>
          <p className="font-mono text-11 tracking-wider text-faint-on-navy">{answer.status === "answered" ? t("sources") : t("related_pages")}</p>
          <ol className="mt-1 space-y-1">
            {answer.sources.map((s) => (
              <li key={s.n} className="text-12 text-muted-on-navy">
                <span className="font-mono">[{s.n}]</span>{" "}
                {s.url ? (
                  <a href={s.url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-cream underline underline-offset-2">
                    <span lang="en">{s.title}</span>
                    <ExternalLink className="size-3" aria-hidden="true" />
                    <span className="sr-only">{t("opens_new_tab")}</span>
                  </a>
                ) : (
                  <span className="text-cream" lang="en">
                    {s.title}
                  </span>
                )}
                {s.retrieved && (
                  <span>
                    {" "}
                    · {t("read_on")} {s.retrieved}
                  </span>
                )}
              </li>
            ))}
          </ol>
        </div>
      )}

      {retryable && (
        <Button variant="secondary" size="sm" className="mt-3" onClick={onRetry}>
          <span lang={language}>{t("try_again")}</span>
        </Button>
      )}
      <p className="mt-3 text-11 text-faint-on-navy" lang={answer.language ?? "en"}>
        {answer.disclaimer}
      </p>
    </li>
  );
}
