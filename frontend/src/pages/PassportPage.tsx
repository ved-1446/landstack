import { ArrowLeft, FileX } from "lucide-react";
import { useMemo } from "react";
import { Link, useNavigate, useParams } from "react-router";
import { useAuth } from "../auth";
import { EmptyState, GlassCard } from "../components/ui";
import { PassportDrawer } from "../features/passport/PassportDrawer";
import { useAppData } from "../lib/appData";
import { isUlpin } from "../lib/format";
import type { ConflictType } from "../types";

/**
 * /app/plots/:ulpin: the land passport as a normal page (the same content the map drawer shows): the checks with their points,
 * the plain-words explanation with the EN / हिन्दी / मराठी switch, the PDF download and Verify. The server decides who may see it:
 * a citizen asking for a plot that is not theirs gets the same "not found" as for a plot that does not exist.
 */
export default function PassportPage() {
  const { ulpin = "" } = useParams();
  const { session } = useAuth();
  const { types } = useAppData();
  const navigate = useNavigate();
  const rules = useMemo(() => {
    const byType: Partial<Record<ConflictType, string>> = {};
    (types.data ?? []).forEach((info) => (byType[info.type] = info.description));
    return byType;
  }, [types.data]);
  const simulated = useMemo(() => new Set<ConflictType>((types.data ?? []).filter((i) => i.simulated).map((i) => i.type)), [types.data]);
  if (!session) return null;
  const back = "/app/plots"; // the plots list of this role (cards for a citizen, a table for staff)

  return (
    <section className="mx-auto max-w-2xl">
      <Link to={back} className="inline-flex items-center gap-2 rounded-control text-14 text-muted-on-navy hover:text-cream">
        <ArrowLeft className="size-4" aria-hidden="true" />
        {session.role === "citizen" ? "Back to my plots" : "Back to all plots"}
      </Link>
      <div className="mt-4">
        {isUlpin(ulpin) ? (
          <PassportDrawer key={ulpin} variant="page" ulpin={ulpin} role={session.role} rules={rules} simulatedTypes={simulated} prefetched={null} onClose={() => navigate(back)} onLoaded={() => undefined} />
        ) : (
          <GlassCard>
            <EmptyState icon={FileX} title="Plot not found" description="A plot id has 14 capital letters and digits, like MH000100000006." />
          </GlassCard>
        )}
      </div>
    </section>
  );
}
