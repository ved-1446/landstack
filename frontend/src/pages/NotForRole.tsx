import { LockKeyhole } from "lucide-react";
import { Link } from "react-router";
import { useAuth } from "../auth";
import { EmptyState, GlassCard } from "../components/ui";
import { prettyRole } from "../constants";
import { HOME } from "../lib/nav";

/** Shown instead of a blank screen when someone opens a page that belongs to another role. The server checks the data again. */
export default function NotForRole() {
  const { session } = useAuth();
  if (!session) return null;
  return (
    <GlassCard className="mx-auto mt-8 max-w-xl" role="alert">
      <EmptyState
        icon={LockKeyhole}
        title="This page is not for your role"
        description={`You are signed in as ${prettyRole(session.role)}. This page is made for another role, so it is not shown here. Nothing is wrong with your account.`}
        action={
          <Link to={HOME[session.role]} className="inline-flex h-11 items-center rounded-control bg-coral px-4 text-14 font-medium text-navy-950 hover:bg-coral-hover">
            Go to my home page
          </Link>
        }
      />
    </GlassCard>
  );
}
