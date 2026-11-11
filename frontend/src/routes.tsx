import { lazy, type ReactNode } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router";
import { useAuth } from "./auth";
import { allowedPaths, HOME } from "./lib/nav";
import AppShell from "./shells/AppShell";
import PublicShell from "./shells/PublicShell";

// Route-level code splitting: each page is its own file that is downloaded only when it is opened. The map (MapLibre, about a
// megabyte) therefore loads only on /app/map, and the Land Guide text only on /app/guide.
const Landing = lazy(() => import("./pages/Landing"));
const HowItWorks = lazy(() => import("./pages/HowItWorks"));
const About = lazy(() => import("./pages/About"));
const VerifyPage = lazy(() => import("./pages/VerifyPage"));
const LoginScreen = lazy(() => import("./screens/LoginScreen"));
const MapPage = lazy(() => import("./pages/MapPage"));
const GuidePage = lazy(() => import("./pages/GuidePage"));
const ActivityPage = lazy(() => import("./pages/ActivityPage"));
const PassportPage = lazy(() => import("./pages/PassportPage"));
const CitizenHome = lazy(() => import("./pages/citizen/CitizenHome"));
const CitizenPlots = lazy(() => import("./pages/citizen/CitizenPlots"));
const CitizenVerify = lazy(() => import("./pages/citizen/CitizenVerify"));
const Dashboard = lazy(() => import("./pages/officer/Dashboard"));
const AdminOverview = lazy(() => import("./pages/admin/Overview"));
const AuditLog = lazy(() => import("./pages/admin/AuditLog"));
const Users = lazy(() => import("./pages/admin/Users"));
const System = lazy(() => import("./pages/admin/System"));
const Insights = lazy(() => import("./pages/admin/Insights"));
const PlotsTable = lazy(() => import("./pages/officer/PlotsTable"));
const Conflicts = lazy(() => import("./pages/officer/Conflicts"));
const Construction = lazy(() => import("./pages/officer/Construction"));
const Zones = lazy(() => import("./pages/officer/Zones"));

/** Only a signed-in person gets past this; a visitor is sent to /login (and brought back afterwards). */
export function RequireAuth({ children }: { children: ReactNode }) {
  const { session } = useAuth();
  const location = useLocation();
  if (!session) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  return children;
}

function RoleHome() {
  const { session } = useAuth();
  return <Navigate to={session ? HOME[session.role] : "/login"} replace />;
}

/** /app/plots shows cards for a citizen and a table for staff. */
function PlotsPage() {
  const { session } = useAuth();
  return session?.role === "citizen" ? <CitizenPlots /> : <PlotsTable />;
}

/** /app/dashboard: the officer's dashboard for an officer, the system-and-people Overview for an admin. */
function DashboardPage() {
  const { session } = useAuth();
  return session?.role === "admin" ? <AdminOverview /> : <Dashboard />;
}

function RoleLogin() {
  const { session } = useAuth();
  const location = useLocation();
  if (session) {
    const from = (location.state as { from?: string } | null)?.from;
    return <Navigate to={from && allowedPaths(session.role).includes(from) ? from : HOME[session.role]} replace />;
  }
  return <LoginScreen />;
}

/**
 * Every URL of the app. Kept separate from the router so the tests can mount it in a memory router.
 * Which /app page a ROLE may open is decided once, in AppShell (a page for another role shows "not for your role").
 */
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
        <Route path="home" element={<CitizenHome />} />
        <Route path="plots" element={<PlotsPage />} />
        <Route path="plots/:ulpin" element={<PassportPage />} />
        <Route path="verify" element={<CitizenVerify />} />
        <Route path="activity" element={<ActivityPage />} />
        <Route path="guide" element={<GuidePage />} />
        <Route path="dashboard" element={<DashboardPage />} />
        <Route path="desk" element={<Dashboard />} />
        <Route path="map" element={<MapPage />} />
        <Route path="conflicts" element={<Conflicts />} />
        <Route path="construction" element={<Construction />} />
        <Route path="zones" element={<Zones />} />
        <Route path="audit" element={<AuditLog />} />
        <Route path="users" element={<Users />} />
        <Route path="system" element={<System />} />
        <Route path="insights" element={<Insights />} />
        <Route path="*" element={<RoleHome />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
