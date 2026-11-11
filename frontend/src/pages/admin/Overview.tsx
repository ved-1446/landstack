import { ArrowRight, ScrollText } from "lucide-react";
import { Link } from "react-router";
import { getAdminSystem, getAdminUsers, getAuditLog } from "../../api";
import { Async } from "../../components/Async";
import { GlassCard, PageHeader, StatCard } from "../../components/ui";
import { useFetch } from "../../hooks";
import { actionIcon } from "../../lib/actionIcon";
import { actionWords, when } from "../../lib/format";
import { sinceFor } from "./AuditLog";
import { StatusTile } from "./shared";

/** The admin's Overview: how the SYSTEM and the PEOPLE are doing (health, accounts, activity, the model). The plot queue is the officer's. */
export default function Overview() {
  const system = useFetch((signal) => getAdminSystem(signal), []);
  const users = useFetch((signal) => getAdminUsers(signal), []);
  const day = useFetch((signal) => getAuditLog({ since: sinceFor("24h"), limit: 1 }, signal), []);
  const week = useFetch((signal) => getAuditLog({ since: sinceFor("7d"), limit: 1 }, signal), []);
  const recent = useFetch((signal) => getAuditLog({ limit: 8 }, signal), []);

  return (
    <section>
      <PageHeader eyebrow="CONTROL ROOM" title="Is everything" emphasis="running?" subtitle="The health of the system, who has access, and what people have been doing. Plots and conflicts are on the Work desk." />

      <div className="mt-8">
        <Async state={system} what="the system status">
          {(s) => (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <StatusTile name="API" status={s.api}  index={0} />
              <StatusTile name="Database" status={s.database}  index={1} />
              <StatusTile name="PostGIS" status={s.postgis}  index={2} />
              <StatusTile name="AI explainer" status={s.ai_explainer}  index={3} />
            </div>
          )}
        </Async>
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-[1fr_1.2fr]">
        <div className="space-y-6">
          <GlassCard>
            <h2 className="font-serif text-26 text-cream">People</h2>
            <div className="mt-4">
              <Async state={users} what="the people">
                {(rows) => (
                  <div className="grid grid-cols-3 gap-3">
                    {(["admin", "officer", "citizen"] as const).map((role) => (
                      <StatCard key={role} label={role === "admin" ? "Admins" : role === "officer" ? "Officers" : "Citizens"} value={rows.filter((u) => u.role === role).length} />
                    ))}
                  </div>
                )}
              </Async>
              <Link to="/app/users" className="mt-4 inline-flex items-center gap-2 text-14 text-cream underline underline-offset-4">
                See everyone
                <ArrowRight className="size-4" aria-hidden="true" />
              </Link>
            </div>
          </GlassCard>

          <GlassCard>
            <h2 className="font-serif text-26 text-cream">Activity</h2>
            <div className="mt-4 grid grid-cols-2 gap-3">
              <Async state={day} what="today's activity">
                {(d) => <StatCard label="Last 24 hours" value={d.total} hint="actions" />}
              </Async>
              <Async state={week} what="this week's activity">
                {(d) => <StatCard label="Last 7 days" value={d.total} hint="actions" />}
              </Async>
            </div>
          </GlassCard>

          <GlassCard>
            <h2 className="font-serif text-26 text-cream">The unusual-plot model</h2>
            <Async state={system} what="the model status">
              {(s) => (
                <p className="mt-2 text-14 text-muted-on-navy">
                  {s.model.loaded
                    ? `Loaded. It learned from ${s.model.trained_on_plots?.toLocaleString("en-IN")} generated plots. It adds a hint to passports and never changes a score.`
                    : "No model is loaded, so passports show no unusual note."}
                </p>
              )}
            </Async>
            <Link to="/app/insights" className="mt-3 inline-flex items-center gap-2 text-14 text-cream underline underline-offset-4">
              What it pays attention to
              <ArrowRight className="size-4" aria-hidden="true" />
            </Link>
          </GlassCard>
        </div>

        <GlassCard>
          <h2 className="font-serif text-26 text-cream">Latest activity</h2>
          <div className="mt-4">
            <Async
              state={recent}
              what="the latest activity"
              isEmpty={(d) => d.rows.length === 0}
              empty={{ icon: ScrollText, title: "Nothing yet", description: "Nobody has opened a passport or asked the Land Guide yet." }}
            >
              {(d) => (
                <ol aria-label="Latest activity" className="relative border-l border-glass-border pl-6">
                  {d.rows.map((row) => {
                    const Icon = actionIcon(row.action);
                    return (
                      <li key={row.id} className="relative pb-4 last:pb-0">
                        <span aria-hidden="true" className="absolute -left-9 flex size-6 items-center justify-center rounded-pill border border-glass-border bg-navy-900">
                          <Icon className="size-3 text-cream" />
                        </span>
                        <p className="text-14 text-cream">
                          <span className="font-mono">{row.username}</span> · {actionWords(row.action)}
                        </p>
                        <p className="text-13 text-muted-on-navy">{when(row.looked_at)}</p>
                      </li>
                    );
                  })}
                </ol>
              )}
            </Async>
          </div>
          <Link to="/app/audit" className="mt-4 inline-flex items-center gap-2 text-14 text-cream underline underline-offset-4">
            Open the audit log
            <ArrowRight className="size-4" aria-hidden="true" />
          </Link>
        </GlassCard>
      </div>
    </section>
  );
}
