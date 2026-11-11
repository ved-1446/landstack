import { Navigate, Route, Routes, useLocation } from "react-router";
import type { ReactNode } from "react";
import { useAuth } from "./auth";
import { allowedPaths, HOME } from "./lib/nav";
import GuidePage from "./pages/GuidePage";
import Landing from "./pages/Landing";
import { About, HowItWorks } from "./pages/InfoPages";
import MapPage from "./pages/MapPage";
import Placeholder from "./pages/Placeholder";
import VerifyPage from "./pages/VerifyPage";
import LoginScreen from "./screens/LoginScreen";
import AppShell from "./shells/AppShell";
import PublicShell from "./shells/PublicShell";

/** Only a signed-in person gets past this; a visitor is sent to /login (and brought back afterwards). */
export function RequireAuth({ children }: { children: ReactNode }) {
  const { session } = useAuth();
  const location = useLocation();
  if (!session) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  return children;
}

/** A page that exists only for some roles: anyone else is sent to their own home page. (The server checks the data again.) */
function RoleGuard({ path, children }: { path: string; children: ReactNode }) {
  const { session } = useAuth();
  if (!session) return null;
  if (!allowedPaths(session.role).includes(path)) return <Navigate to={HOME[session.role]} replace />;
  return children;
}

function RoleHome() {
  const { session } = useAuth();
  return <Navigate to={session ? HOME[session.role] : "/login"} replace />;
}

/** The page behind /app/plots depends on who is signed in (officers: all plots; citizens: their own). Both are built in 13b. */
function PlotsPage() {
  const { session } = useAuth();
  return session?.role === "citizen" ? (
    <Placeholder title="My" emphasis="plots" showMapLink />
  ) : (
    <Placeholder title="All" emphasis="plots" showMapLink />
  );
}

const PLACEHOLDERS: Record<string, { title: string; emphasis: string }> = {
  "/app/home": { title: "Welcome", emphasis: "home" },
  "/app/dashboard": { title: "Your", emphasis: "dashboard" },
  "/app/activity": { title: "Your", emphasis: "activity" },
  "/app/conflicts": { title: "Open", emphasis: "conflicts" },
  "/app/construction": { title: "New", emphasis: "construction" },
  "/app/audit": { title: "Audit", emphasis: "log" },
  "/app/users": { title: "People and", emphasis: "access" },
  "/app/system": { title: "System", emphasis: "health" },
  "/app/insights": { title: "Model", emphasis: "insights" },
};

function RoleLogin() {
  const { session } = useAuth();
  const location = useLocation();
  if (session) {
    const from = (location.state as { from?: string } | null)?.from;
    return <Navigate to={from && allowedPaths(session.role).includes(from) ? from : HOME[session.role]} replace />;
  }
  return <LoginScreen />;
}

/** Every URL of the app. Kept separate from the router so the tests can mount it in a memory router. */
export function AppRoutes() {
  return (
    <Routes>
      <Route element={<PublicShell />}>
        <Route index element={<Landing />} />
        <Route path="how-it-works" element={<HowItWorks />} />
        <Route path="about" element={<About />} />
        <Route path="verify" element={<VerifyPage />} />
      </Route>
      <Route path="login" element={<RoleLogin />} />
      <Route
        path="app"
        element={
          <RequireAuth>
            <AppShell />
          </RequireAuth>
        }
      >
        <Route index element={<RoleHome />} />
        <Route path="plots" element={<RoleGuard path="/app/plots"><PlotsPage /></RoleGuard>} />
        <Route path="map" element={<RoleGuard path="/app/map"><MapPage /></RoleGuard>} />
        <Route path="guide" element={<RoleGuard path="/app/guide"><GuidePage /></RoleGuard>} />
        {Object.entries(PLACEHOLDERS).map(([path, props]) => (
          <Route key={path} path={path.replace("/app/", "")} element={<RoleGuard path={path}><Placeholder {...props} /></RoleGuard>} />
        ))}
        <Route path="*" element={<RoleHome />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
