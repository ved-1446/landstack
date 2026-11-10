import { AlertTriangle, CircleHelp, Clock, ExternalLink, PowerOff, SendHorizontal, Sparkles } from "lucide-react";
import { useCallback, useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { askGuide } from "../../api";
import { Button, Chip, Popover } from "../../components/ui";
import { cn } from "../../lib/cn";
import type { GuideAnswer, GuideStatus } from "../../types";

const MAX_QUESTION = 500; // the same limit the API enforces
const SUGGESTIONS = ["What is a ULPIN?", "What does the amber band mean?", "How does mutation of land work?"];

type Message =
  | { id: number; kind: "user"; text: string }
  | { id: number; kind: "answer"; question: string; answer: GuideAnswer }
  | { id: number; kind: "error"; question: string; text: string };

// Every state is written in words with an icon, never shown by colour alone.
const STATUS: Record<GuideStatus, { icon: typeof Sparkles; label: string }> = {
  answered: { icon: Sparkles, label: "AI answer, from the sources" },
  no_sources: { icon: CircleHelp, label: "Not in my sources" },
  ai_off: { icon: PowerOff, label: "AI is off" },
  ai_busy: { icon: Clock, label: "AI is busy" },
  ai_failed: { icon: AlertTriangle, label: "AI could not answer" },
};

interface GuidePanelProps {
  open: boolean;
  onClose: () => void;
}

/**
 * The Land Guide chat. It stays mounted when the panel is closed, so the conversation is kept until the page is reloaded
 * (it is held in memory only and never stored). Only the question text is sent: no plot, no personal data.
 */
export function GuidePanel({ open, onClose }: GuidePanelProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const nextId = useRef(1);
  const abort = useRef<AbortController | null>(null);
  const end = useRef<HTMLDivElement>(null);

  useEffect(() => () => abort.current?.abort(), []);
  useEffect(() => {
    if (open) end.current?.scrollIntoView({ block: "end" });
  }, [open, messages, loading]);

  const ask = useCallback(async (question: string, addUserMessage: boolean) => {
    const clean = question.trim();
    if (!clean) return;
    setMessages((old) => (addUserMessage ? [...old, { id: nextId.current++, kind: "user", text: clean }] : old));
    setLoading(true);
    abort.current?.abort();
    const controller = new AbortController();
    abort.current = controller;
    try {
      const answer = await askGuide(clean, controller.signal);
      setMessages((old) => [...old, { id: nextId.current++, kind: "answer", question: clean, answer }]);
    } catch (err) {
      if (controller.signal.aborted) return;
      const message = err instanceof Error ? err.message : "Something went wrong.";
      setMessages((old) => [...old, { id: nextId.current++, kind: "error", question: clean, text: message }]);
    }
    setLoading(false);
  }, []);

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
    <form onSubmit={submit}>
      <label htmlFor="guide-input" className="sr-only">
        Your question for the Land Guide
      </label>
      <textarea
        id="guide-input"
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={onKeyDown}
        maxLength={MAX_QUESTION}
        rows={2}
        placeholder="Ask about land records in general…"
        className="w-full resize-none rounded-control border border-line-on-navy bg-navy-950 px-3 py-2 text-14 text-cream placeholder:text-faint-on-navy"
      />
      <div className="mt-2 flex items-center justify-between gap-3">
        <p className="text-11 text-faint-on-navy">AI can be wrong. Not legal advice. Do not type personal details.</p>
        <Button type="submit" size="sm" loading={loading} disabled={!text.trim()} aria-label="Send question">
          <SendHorizontal className="size-4" aria-hidden="true" />
          Ask
        </Button>
      </div>
    </form>
  );

  return (
    <Popover open={open} onClose={onClose} title="Land Guide" footer={footer} className="md:w-(--guide-width)">
      <div className="mt-2 flex items-start gap-2 rounded-card border border-line-on-navy bg-navy-900 p-3">
        <Chip>AI</Chip>
        <p className="text-12 text-muted-on-navy">
          I answer only from a few public pages (Vikaspedia) and the LandStack glossary. I can be wrong, and I am not legal advice.
        </p>
      </div>

      {messages.length === 0 && !loading && (
        <div className="mt-4">
          <p className="mb-2 font-mono text-11 tracking-wider text-faint-on-navy">TRY ASKING</p>
          <ul className="flex flex-wrap gap-2">
            {SUGGESTIONS.map((q) => (
              <li key={q}>
                <Chip onClick={() => void ask(q, true)}>{q}</Chip>
              </li>
            ))}
          </ul>
        </div>
      )}

      <ol aria-label="Conversation" aria-live="polite" className="mt-4 space-y-3">
        {messages.map((m) =>
          m.kind === "user" ? (
            <li key={m.id} className="ml-8 rounded-card bg-navy-800 p-3">
              <p className="mb-1 font-mono text-11 tracking-wider text-faint-on-navy">YOU</p>
              <p className="whitespace-pre-wrap text-14 text-cream">{m.text}</p>
            </li>
          ) : m.kind === "answer" ? (
            <AnswerBubble key={m.id} answer={m.answer} onRetry={() => retry(m.question, m.id)} />
          ) : (
            <li key={m.id} className="mr-8 rounded-card border border-line-on-navy bg-navy-900 p-3">
              <Chip>
                <AlertTriangle className="size-3" aria-hidden="true" />
                Could not ask
              </Chip>
              <p className="mt-2 text-13 text-cream">{m.text}</p>
              <Button variant="secondary" size="sm" className="mt-3" onClick={() => retry(m.question, m.id)}>
                Try again
              </Button>
            </li>
          ),
        )}
        {loading && (
          <li role="status" className="mr-8 flex items-center gap-2 rounded-card border border-line-on-navy bg-navy-900 p-3 text-13 text-muted-on-navy">
            <Clock className="size-4" aria-hidden="true" />
            Looking through the sources…
          </li>
        )}
      </ol>
      <div ref={end} />
    </Popover>
  );
}

function AnswerBubble({ answer, onRetry }: { answer: GuideAnswer; onRetry: () => void }) {
  const status = STATUS[answer.status];
  const retryable = answer.status === "ai_busy" || answer.status === "ai_failed";
  return (
    <li className="mr-8 rounded-card border border-line-on-navy bg-navy-900 p-3">
      <Chip>
        <status.icon className="size-3" aria-hidden="true" />
        {status.label}
      </Chip>
      <p className={cn("mt-2 whitespace-pre-wrap text-14 text-cream")}>{answer.answer}</p>

      {answer.sources.length > 0 && (
        <div className="mt-3">
          <p className="font-mono text-11 tracking-wider text-faint-on-navy">{answer.status === "answered" ? "SOURCES" : "RELATED PAGES"}</p>
          <ol className="mt-1 space-y-1">
            {answer.sources.map((s) => (
              <li key={s.n} className="text-12 text-muted-on-navy">
                <span className="font-mono">[{s.n}]</span>{" "}
                {s.url ? (
                  <a href={s.url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-cream underline underline-offset-2">
                    {s.title}
                    <ExternalLink className="size-3" aria-hidden="true" />
                    <span className="sr-only">(opens in a new tab)</span>
                  </a>
                ) : (
                  <span className="text-cream">{s.title}</span>
                )}
                {s.retrieved && <span> · read {s.retrieved}</span>}
              </li>
            ))}
          </ol>
        </div>
      )}

      {retryable && (
        <Button variant="secondary" size="sm" className="mt-3" onClick={onRetry}>
          Try again
        </Button>
      )}
      <p className="mt-3 text-11 text-faint-on-navy">{answer.disclaimer}</p>
    </li>
  );
}
