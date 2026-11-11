import { ChevronLeft, ChevronRight, ScrollText } from "lucide-react";
import { useMemo, useState } from "react";
import { Link } from "react-router";
import { getAdminUsers, getAuditLog } from "../../api";
import { Async } from "../../components/Async";
import { Button, Chip, GlassCard, PageHeader, RoleBadge } from "../../components/ui";
import { useFetch } from "../../hooks";
import { actionIcon } from "../../lib/actionIcon";
import { ACTION_WORDS, actionWords, when } from "../../lib/format";

export const PAGE_SIZE = 20;
export const RANGES = [
  { key: "24h", label: "Last 24 hours", hours: 24 },
  { key: "7d", label: "Last 7 days", hours: 24 * 7 },
  { key: "30d", label: "Last 30 days", hours: 24 * 30 },
  { key: "all", label: "All time", hours: 0 },
] as const;
export type RangeKey = (typeof RANGES)[number]["key"];

/** The ISO time a preset starts at ("" for all time). */
export function sinceFor(range: RangeKey, now = Date.now()): string | undefined {
  const hours = RANGES.find((r) => r.key === range)?.hours ?? 0;
  return hours ? new Date(now - hours * 3_600_000).toISOString() : undefined;
}

/** Audit log: a timeline of who looked at what, newest first, with filters (user, kind of action, time range) and pages. */
export default function AuditLog() {
  const [username, setUsername] = useState("");
  const [action, setAction] = useState("");
  const [range, setRange] = useState<RangeKey>("7d");
  const [page, setPage] = useState(1);
  const people = useFetch((signal) => getAdminUsers(signal), []);
  const state = useFetch(
    (signal) => getAuditLog({ username: username || undefined, action: action || undefined, since: sinceFor(range), limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE }, signal),
    [username, action, range, page],
    true,
  );
  const pages = Math.max(1, Math.ceil((state.data?.total ?? 0) / PAGE_SIZE));
  const names = useMemo(() => (people.data ?? []).map((u) => u.username), [people.data]);
  const change = (fn: () => void) => {
    fn();
    setPage(1);
  };

  return (
    <section>
      <PageHeader eyebrow="CONTROL ROOM" title="Who looked at" emphasis="what" subtitle="Every passport view, PDF download, explanation and Land Guide question, newest first. The question text itself is never stored." />
      <GlassCard className="mt-8">
        <div className="flex flex-wrap items-end gap-4">
          <div className="max-sm:w-full">
            <label htmlFor="audit-user" className="mb-2 block text-13 text-muted-on-navy">
              Person
            </label>
            <select id="audit-user" value={username} onChange={(e) => change(() => setUsername(e.target.value))} className="h-11 w-full max-w-full rounded-control border border-glass-border bg-navy-950 px-3 text-14 text-cream sm:w-auto">
              <option value="">Everyone</option>
              {names.map((n) => (
                <option key={n} value={n}>
                  {n}
                </option>
              ))}
            </select>
          </div>
          <div className="max-sm:w-full">
            <label htmlFor="audit-action" className="mb-2 block text-13 text-muted-on-navy">
              Kind of action
            </label>
            <select id="audit-action" value={action} onChange={(e) => change(() => setAction(e.target.value))} className="h-11 w-full max-w-full rounded-control border border-glass-border bg-navy-950 px-3 text-14 text-cream sm:w-auto">
              <option value="">Every kind</option>
              {Object.entries(ACTION_WORDS).map(([key, words]) => (
                <option key={key} value={key}>
                  {words}
                </option>
              ))}
            </select>
          </div>
          <fieldset>
            <legend className="mb-2 text-13 text-muted-on-navy">When</legend>
            <div className="flex flex-wrap gap-2">
              {RANGES.map((r) => (
                <Chip key={r.key} pressed={range === r.key} onClick={() => change(() => setRange(r.key))}>
                  {r.label}
                </Chip>
              ))}
            </div>
          </fieldset>
        </div>

        <div className="mt-6">
          <Async
            state={state}
            what="the audit log"
            isEmpty={(d) => d.rows.length === 0}
            empty={{ icon: ScrollText, title: "Nothing matches", description: "No actions were recorded for this person, kind of action and time range." }}
          >
            {(d) => (
              <>
                <p className="text-13 text-muted-on-navy" aria-live="polite">
                  {d.total.toLocaleString("en-IN")} {d.total === 1 ? "entry" : "entries"}. Page {Math.min(page, pages)} of {pages}.
                </p>
                <ol aria-label="Audit timeline" className="relative mt-4 border-l border-glass-border pl-6">
                  {d.rows.map((row) => {
                    const Icon = actionIcon(row.action);
                    return (
                      <li key={row.id} className="relative pb-5 last:pb-0">
                        <span aria-hidden="true" className="absolute -left-9 flex size-6 items-center justify-center rounded-pill border border-glass-border bg-navy-900">
                          <Icon className="size-3 text-cream" />
                        </span>
                        <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                          <span className="font-mono text-14 text-cream">{row.username}</span>
                          <RoleBadge role={row.role} />
                          <time dateTime={row.looked_at} className="text-13 text-muted-on-navy">
                            {when(row.looked_at)}
                          </time>
                        </div>
                        <p className="mt-1 text-14 text-cream">
                          {actionWords(row.action)}
                          {row.ulpin && (
                            <>
                              {" "}
                              <Link to={`/app/plots/${row.ulpin}`} className="font-mono text-muted-on-navy underline underline-offset-4">
                                {row.ulpin}
                              </Link>
                            </>
                          )}
                        </p>
                      </li>
                    );
                  })}
                </ol>
                <nav aria-label="Pages" className="mt-6 flex items-center justify-between gap-3">
                  <Button variant="secondary" size="sm" disabled={page <= 1} onClick={() => setPage(page - 1)}>
                    <ChevronLeft className="size-4" aria-hidden="true" />
                    Newer
                  </Button>
                  <p className="text-13 text-muted-on-navy">
                    Page {Math.min(page, pages)} of {pages}
                  </p>
                  <Button variant="secondary" size="sm" disabled={page >= pages} onClick={() => setPage(page + 1)}>
                    Older
                    <ChevronRight className="size-4" aria-hidden="true" />
                  </Button>
                </nav>
              </>
            )}
          </Async>
        </div>
      </GlassCard>
    </section>
  );
}
