import { UsersRound } from "lucide-react";
import { getAdminUsers } from "../../api";
import { Async } from "../../components/Async";
import { DataList, GlassCard, PageHeader, RoleBadge } from "../../components/ui";
import { useFetch } from "../../hooks";
import { when } from "../../lib/format";

/** Users: who has an account, their role, how many plots are linked to them and when they last did something. No passwords, ever. */
export default function Users() {
  const state = useFetch((signal) => getAdminUsers(signal), []);
  return (
    <section>
      <PageHeader eyebrow="CONTROL ROOM" title="People and" emphasis="access" subtitle="Everyone who can sign in, what they may see, and when they were last active. Passwords are never shown: only a one-way hash is stored." />
      <GlassCard className="mt-8">
        <Async
          state={state}
          what="the users"
          isEmpty={(rows) => rows.length === 0}
          empty={{ icon: UsersRound, title: "No users", description: "There are no accounts yet. Run db/seed_users.py to create the demo accounts." }}
        >
          {(rows) => (
            <DataList
              label="Users"
              rows={rows.map((u) => ({
                key: u.username,
                primary: <span className="font-mono">{u.username}</span>,
                secondary: (
                  <>
                    {u.role === "citizen" ? `${u.plots} ${u.plots === 1 ? "plot" : "plots"} linked · ` : ""}
                    {u.last_active ? `last active ${when(u.last_active)}` : "never active"} · {u.actions_30d} {u.actions_30d === 1 ? "action" : "actions"} in 30 days
                  </>
                ),
                trailing: <RoleBadge role={u.role} />,
              }))}
            />
          )}
        </Async>
      </GlassCard>
    </section>
  );
}
