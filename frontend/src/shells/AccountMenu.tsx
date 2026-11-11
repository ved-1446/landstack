import { History, LogOut, User } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router";
import { useAuth } from "../auth";
import { prettyRole } from "../constants";

/** The account button in the top bar: shows who is signed in and has the Sign out button. */
export function AccountMenu() {
  const { session, signOut } = useAuth();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const box = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => event.key === "Escape" && setOpen(false);
    const onPointer = (event: PointerEvent) => {
      if (!box.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("keydown", onKey);
    document.addEventListener("pointerdown", onPointer);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("pointerdown", onPointer);
    };
  }, [open]);

  if (!session) return null;
  return (
    <div ref={box} className="relative">
      <button
        type="button"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={`Account: ${session.username}`}
        onClick={() => setOpen((v) => !v)}
        className="flex size-10 items-center justify-center rounded-pill border border-glass-border bg-glass-fill text-cream transition-colors duration-150 hover:bg-glass-fill-strong"
      >
        <User className="size-5" aria-hidden="true" />
      </button>
      {open && (
        <div role="menu" aria-label="Account" className="glass absolute right-0 top-12 w-60 rounded-panel p-4 shadow-2">
          <p className="font-mono text-14 text-cream">{session.username}</p>
          <p className="mt-1 text-13 text-muted-on-navy">
            {prettyRole(session.role)}.{" "}
            {session.role === "citizen" ? "You can see only the plots you own." : "You can see every plot and its passport."}
          </p>
          {session.role !== "citizen" && (
            <Link
              to="/app/activity"
              role="menuitem"
              onClick={() => setOpen(false)}
              className="mt-3 flex h-11 w-full items-center justify-center gap-2 rounded-control glass-card text-14 text-cream hover:bg-glass-fill-strong"
            >
              <History className="size-4" aria-hidden="true" />
              My activity
            </Link>
          )}
          <button
            type="button"
            role="menuitem"
            onClick={() => {
              signOut();
              navigate("/", { replace: true });
            }}
            className="mt-3 flex h-11 w-full items-center justify-center gap-2 rounded-control glass-card text-14 text-cream hover:bg-glass-fill-strong"
          >
            <LogOut className="size-4" aria-hidden="true" />
            Sign out
          </button>
        </div>
      )}
    </div>
  );
}
