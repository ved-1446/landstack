import { History } from "lucide-react";
import { Link } from "react-router";
import { getMyActivity } from "../api";
import { useAuth } from "../auth";
import { Async } from "../components/Async";
import { GlassCard, PageHeader } from "../components/ui";
import { ROLE_IDENTITY } from "../components/ui/RoleBadge";
import { actionIcon } from "../lib/actionIcon";
import { actionWords, when } from "../lib/format";
import { useFetch } from "../hooks";

/** My own recent actions: passport views, PDF downloads, explanations and Land Guide questions, newest first. Nobody else's. */
export default function ActivityPage() {
  const { session } = useAuth();
  const state = useFetch((signal) => getMyActivity(50, signal), []);
  if (!session) return null;
  return (
    <section>
      <PageHeader eyebrow={ROLE_IDENTITY[session.role].area} title="My recent" emphasis="activity" subtitle="What you did lately in LandStack. Only you can see this list. The Land Guide question itself is never stored." />
      <GlassCard className="mt-8">
        <Async
          state={state}
          what="your activity"
          isEmpty={(d) => d.length === 0}
          empty={{ icon: History, title: "Nothing here yet", description: "When you open a passport, download a PDF or ask the Land Guide, it shows up here.", action: <Link to="/app/plots" className="text-14 text-cream underline underline-offset-4">Go to the plots</Link> }}
        >
          {(rows) => (
            <ul aria-label="My recent activity" className="divide-y divide-glass-border">
              {rows.map((row) => {
                const Icon = actionIcon(row.action);
                return (
                  <li key={row.id} className="flex items-center gap-3 py-3">
                    <Icon className="size-5 shrink-0 text-muted-on-navy" aria-hidden="true" />
                    <div className="min-w-0 flex-1">
                      <p className="text-14 text-cream">{actionWords(row.action)}</p>
                      {row.ulpin && (
                        <Link to={`/app/plots/${row.ulpin}`} className="font-mono text-13 text-muted-on-navy underline underline-offset-4">
                          {row.ulpin}
                        </Link>
                      )}
                    </div>
                    <time dateTime={row.looked_at} className="shrink-0 text-13 text-muted-on-navy">
                      {when(row.looked_at)}
                    </time>
                  </li>
                );
              })}
            </ul>
          )}
        </Async>
      </GlassCard>
    </section>
  );
}
