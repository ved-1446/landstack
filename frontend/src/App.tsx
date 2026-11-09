import { useEffect, useState } from "react";
import { getSession, logout, setUnauthorizedHandler } from "./api";
import Dashboard from "./Dashboard";
import Login from "./components/Login";
import type { Session } from "./types";

// Logged in -> the dashboard. Not logged in (or the server said "log in again") -> the login screen.
export default function App() {
  const [session, setSession] = useState<Session | null>(() => getSession());
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    setUnauthorizedHandler(() => {
      setSession(null);
      setNotice("Your session has ended. Please log in again.");
    });
    return () => setUnauthorizedHandler(null);
  }, []);

  if (!session) {
    return <Login notice={notice} onLoggedIn={(s) => { setNotice(null); setSession(s); }} />;
  }
  return (
    <Dashboard
      session={session}
      onLogout={() => { logout(); setNotice(null); setSession(null); }}
    />
  );
}
