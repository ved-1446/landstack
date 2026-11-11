import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { getSession, logout, setUnauthorizedHandler } from "./api";
import type { Session } from "./types";

interface AuthValue {
  session: Session | null;
  /** a message for the login page, for example "Your session has ended." */
  notice: string | null;
  signedIn: (session: Session) => void;
  signOut: () => void;
}

const AuthContext = createContext<AuthValue | null>(null);

/** Holds the login session for the whole app. A 401 from the server (api.ts calls the handler) sends everyone back to /login. */
export function AuthProvider({ children, initial }: { children: ReactNode; initial?: Session | null }) {
  const [session, setSession] = useState<Session | null>(() => (initial !== undefined ? initial : getSession()));
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    setUnauthorizedHandler(() => {
      setSession(null);
      setNotice("Your session has ended. Please sign in again.");
    });
    return () => setUnauthorizedHandler(null);
  }, []);

  const signedIn = useCallback((next: Session) => {
    setNotice(null);
    setSession(next);
  }, []);
  const signOut = useCallback(() => {
    logout();
    setNotice(null);
    setSession(null);
  }, []);

  const value = useMemo(() => ({ session, notice, signedIn, signOut }), [session, notice, signedIn, signOut]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth(): AuthValue {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used inside <AuthProvider>");
  return value;
}
