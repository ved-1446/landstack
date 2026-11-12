import { MotionConfig } from "framer-motion";
import { BrowserRouter } from "react-router";
import { AuthProvider } from "./auth";
import { ServerWakingBanner } from "./components/ServerWakingBanner";
import { ToastProvider } from "./components/ui";
import { AppRoutes } from "./routes";

// Real URLs: / (home), /login, /how-it-works, /about, /verify and the protected /app/*. See routes.tsx.
export default function App() {
  return (
    // reducedMotion="user": every framer-motion animation respects the visitor's reduced-motion setting
    <MotionConfig reducedMotion="user">
      <BrowserRouter>
        <AuthProvider>
          <ToastProvider>
            <AppRoutes />
            <ServerWakingBanner />
          </ToastProvider>
        </AuthProvider>
      </BrowserRouter>
    </MotionConfig>
  );
}
