import { RefreshCw } from "lucide-react";
import { getAdminSystem } from "../../api";
import { Async } from "../../components/Async";
import { Button, GlassCard, PageHeader, StatCard } from "../../components/ui";
import { useFetch } from "../../hooks";
import { when } from "../../lib/format";
import { StatusTile } from "./shared";

const COUNT_LABELS: Record<string, string> = { plots: "Plots", users: "Users", audit_rows: "Audit rows", passports_issued: "Passports issued" };

/** System: is everything running (API, database, PostGIS, the AI explainer), the model, the counts and the versions. Nothing secret. */
export default function System() {
  const state = useFetch((signal) => getAdminSystem(signal), []);
  return (
    <section>
      <PageHeader
        eyebrow="CONTROL ROOM"
        title="System"
        emphasis="health"
        subtitle="What is running, and which versions. The AI explainer is shown as on or off from the settings; this page never calls it."
        actions={
          <Button variant="secondary" onClick={state.retry} loading={state.loading && Boolean(state.data)}>
            <RefreshCw className="size-4" aria-hidden="true" />
            Check again
          </Button>
        }
      />
      <div className="mt-8">
        <Async state={state} what="the system status">
          {(s) => (
            <>
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <StatusTile name="API" status={s.api}  index={0} />
                <StatusTile name="Database" status={s.database}  index={1} />
                <StatusTile name="PostGIS" status={s.postgis}  index={2} />
                <StatusTile name="AI explainer" status={s.ai_explainer}  index={3} />
              </div>
              <p className="mt-3 text-13 text-muted-on-navy">
                Checked {when(s.checked_at)}. The API has been up since {when(s.api_started_at)}.
              </p>

              <div className="mt-6 grid gap-6 lg:grid-cols-2">
                <GlassCard>
                  <h2 className="font-serif text-26 text-cream">The unusual-plot model</h2>
                  <dl className="mt-4 space-y-3 text-14">
                    <Row label="Loaded" value={s.model.loaded ? "Yes" : "No (the passport simply shows no unusual note)"} />
                    <Row label="Kind" value={s.model.kind} />
                    {s.model.loaded && <Row label="Trained on" value={`${s.model.trained_on_plots?.toLocaleString("en-IN")} generated plots${s.model.trained_on ? `, on ${s.model.trained_on}` : ""}`} />}
                    {s.model.loaded && <Row label="Flags the top" value={`${100 - (s.model.flag_percentile ?? 95)}% most unusual`} />}
                    {s.model.loaded && <Row label="Reasons by" value={s.model.explanation_method === "shap" ? "SHAP" : "distance from the typical value"} />}
                  </dl>
                </GlassCard>
                <GlassCard>
                  <h2 className="font-serif text-26 text-cream">In the database</h2>
                  <div className="mt-4 grid grid-cols-2 gap-4">
                    {Object.entries(s.counts).map(([key, value]) => (
                      <StatCard key={key} label={COUNT_LABELS[key] ?? key} value={value} />
                    ))}
                  </div>
                </GlassCard>
              </div>

              <GlassCard className="mt-6">
                <h2 className="font-serif text-26 text-cream">Versions</h2>
                <p className="mt-1 text-13 text-muted-on-navy">API {s.api_version}</p>
                <dl className="mt-4 grid gap-x-8 gap-y-3 sm:grid-cols-2 lg:grid-cols-3">
                  {Object.entries(s.versions).map(([name, version]) => (
                    <div key={name} className="flex items-baseline justify-between gap-3 border-b border-glass-border pb-2">
                      <dt className="text-13 text-muted-on-navy">{name}</dt>
                      <dd className="font-mono text-13 text-cream">{version}</dd>
                    </div>
                  ))}
                </dl>
              </GlassCard>
            </>
          )}
        </Async>
      </div>
    </section>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-wrap justify-between gap-x-4 gap-y-1 border-b border-glass-border pb-2">
      <dt className="text-muted-on-navy">{label}</dt>
      <dd className="text-right text-cream">{value}</dd>
    </div>
  );
}
