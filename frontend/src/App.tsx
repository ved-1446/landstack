import { MotionConfig } from "framer-motion";
import { useEffect, useState } from "react";
import { getSession, logout, setUnauthorizedHandler } from "./api";
import { ToastProvider } from "./components/ui";
import LoginScreen from "./screens/LoginScreen";
import MapScreen from "./screens/MapScreen";
import type { Session } from "./types";

// Logged in -> the map. Not logged in (or the server said "log in again") -> the login screen.
export default function App() {
  const [session, setSession] = useState<Session | null>(() => getSession());
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    setUnauthorizedHandler(() => {
      setSession(null);
      setNotice("Your session has ended. Please sign in again.");
    });
    return () => setUnauthorizedHandler(null);
  }, []);

  return (
    // reducedMotion="user": every framer-motion animation respects the visitor's reduced-motion setting
    <MotionConfig reducedMotion="user">
      <ToastProvider>
        {session ? (
          <MapScreen
            session={session}
            onLogout={() => {
              logout();
              setNotice(null);
              setSession(null);
            }}
          />
        ) : (
          <LoginScreen
            notice={notice}
            onLoggedIn={(s) => {
              setNotice(null);
              setSession(s);
            }}
          />
        )}
      </ToastProvider>
    </MotionConfig>
  );
}
