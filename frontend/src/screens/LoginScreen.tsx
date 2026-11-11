import { AnimatePresence, motion } from "framer-motion";
import { ArrowLeft, ArrowRight, Building2, Eye, EyeOff, ShieldCheck, UserRound } from "lucide-react";
import { lazy, Suspense, useEffect, useRef, useState, type FormEvent } from "react";
import { Link } from "react-router";
import { ApiError, login } from "../api";
import { useAuth } from "../auth";
import { Button } from "../components/ui";
import { DEMO_ACCOUNTS, DEMO_ACCOUNTS_ENABLED } from "../features/login/demoAccounts";
import { cn } from "../lib/cn";
import { DURATION, EASE_OUT } from "../lib/motion";

// Loaded only when the login screen is shown (it is not part of the map screen's code).
const FlowField = lazy(() => import("../features/login/FlowField"));

function friendlyError(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 401) return "That username or password is not right. Check them and try again.";
    if (error.status === 429) {
      return `Too many sign-in attempts. Please wait ${error.retryAfter ? `${error.retryAfter} seconds` : "a minute"} and try again.`;
    }
    return error.message;
  }
  return "Something went wrong. Please try again.";
}

const inputClass =
  "h-11 w-full rounded-control border border-glass-border bg-navy-950 px-3 text-14 text-cream placeholder:text-faint-on-navy";

// the three demo role cards use these accounts (the passwords are public demo passwords, shown only when VITE_DEMO_ACCOUNTS is true)
const DEMO_CARDS = [
  { username: "citizen1", label: "Citizen", note: "Sees only their own 3 plots", icon: UserRound },
  { username: "officer", label: "Officer", note: "Sees every plot", icon: Building2 },
  { username: "admin", label: "Admin", note: "Sees everything, plus the audit log", icon: ShieldCheck },
] as const;

export default function LoginScreen() {
  const { notice, signedIn } = useAuth();
  const [step, setStep] = useState<1 | 2>(1);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const passwordInput = useRef<HTMLInputElement>(null);
  const usernameInput = useRef<HTMLInputElement>(null);

  useEffect(() => {
    (step === 1 ? usernameInput : passwordInput).current?.focus();
  }, [step]);

  function next(event: FormEvent) {
    event.preventDefault();
    if (!username.trim()) {
      setError("Enter your username to continue.");
      return;
    }
    setError(null);
    setStep(2);
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!password) {
      setError("Enter your password.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      signedIn(await login(username.trim(), password));
    } catch (err) {
      setError(friendlyError(err));
      setBusy(false);
    }
  }

  function fillDemo(account: (typeof DEMO_ACCOUNTS)[number]) {
    setUsername(account.username);
    setPassword(account.password);
    setShowPassword(false);
    setError(null);
    setStep(2);
  }

  const slide = { duration: DURATION.base, ease: EASE_OUT };

  return (
    <main className="relative flex min-h-dvh items-center justify-center overflow-hidden bg-navy-950 p-4">
      <Suspense fallback={null}>
        <FlowField />
      </Suspense>

      <div className="glass-card-strong relative z-panel w-full max-w-md rounded-glass p-8 shadow-3">
        <Link to="/" className="mb-6 inline-flex items-center gap-2 rounded-control text-13 text-muted-on-navy hover:text-cream">
          <ArrowLeft className="size-4" aria-hidden="true" />
          Back to home
        </Link>
        <h1 className="font-serif text-58 text-cream">Sign <em className="text-coral">in</em></h1>
        <p className="mt-2 text-14 text-muted-on-navy">Sign in to see land records. All data here is demo data.</p>

        {notice && (
          <p role="status" className="mt-4 rounded-control border border-line-on-navy bg-navy-800 px-3 py-2 text-13 text-cream">
            {notice}
          </p>
        )}

        <div className="mt-6">
          <AnimatePresence mode="wait" initial={false}>
            {step === 1 ? (
              <motion.form
                key="username"
                onSubmit={next}
                initial={{ opacity: 0, x: -16 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -16 }}
                transition={slide}
                className="space-y-4"
              >
                <div>
                  <label htmlFor="username" className="mb-2 block text-13 text-muted-on-navy">
                    Username
                  </label>
                  <input
                    id="username"
                    ref={usernameInput}
                    value={username}
                    onChange={(e) => {
                      setUsername(e.target.value);
                      setError(null);
                    }}
                    autoComplete="username"
                    autoCapitalize="none"
                    spellCheck={false}
                    className={inputClass}
                  />
                </div>
                <Button type="submit" className="w-full">
                  Continue
                  <ArrowRight className="size-4" aria-hidden="true" />
                </Button>
              </motion.form>
            ) : (
              <motion.form
                key="password"
                onSubmit={submit}
                initial={{ opacity: 0, x: 16 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 16 }}
                transition={slide}
                className="space-y-4"
              >
                <button
                  type="button"
                  onClick={() => {
                    setStep(1);
                    setError(null);
                  }}
                  className="inline-flex items-center gap-2 rounded-control text-13 text-muted-on-navy hover:text-cream"
                >
                  <ArrowLeft className="size-4" aria-hidden="true" />
                  <span className="font-mono">{username}</span>
                </button>
                <div>
                  <label htmlFor="password" className="mb-2 block text-13 text-muted-on-navy">
                    Password
                  </label>
                  <div className="relative">
                    <input
                      id="password"
                      ref={passwordInput}
                      type={showPassword ? "text" : "password"}
                      value={password}
                      onChange={(e) => {
                        setPassword(e.target.value);
                        setError(null);
                      }}
                      autoComplete="current-password"
                      className={cn(inputClass, "pr-12")}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword((shown) => !shown)}
                      aria-label={showPassword ? "Hide password" : "Show password"}
                      className="absolute right-1 top-1/2 flex size-9 -translate-y-1/2 items-center justify-center rounded-control text-muted-on-navy hover:text-cream"
                    >
                      {showPassword ? <EyeOff className="size-4" aria-hidden="true" /> : <Eye className="size-4" aria-hidden="true" />}
                    </button>
                  </div>
                </div>
                <Button type="submit" className="w-full" loading={busy}>
                  Sign in
                </Button>
              </motion.form>
            )}
          </AnimatePresence>

          <div aria-live="polite" className="min-h-6">
            {error && (
              <p role="alert" className="mt-4 rounded-control border border-line-on-navy bg-navy-800 px-3 py-2 text-13 text-cream">
                {error}
              </p>
            )}
          </div>
        </div>

        {DEMO_ACCOUNTS_ENABLED && (
          <section aria-label="Demo accounts" className="mt-6 border-t border-glass-border pt-4">
            <h2 className="font-mono text-11 tracking-widest text-muted-on-navy">TRY A DEMO ACCOUNT</h2>
            <ul className="mt-3 grid grid-cols-3 gap-2 max-sm:grid-cols-1">
              {DEMO_CARDS.map((card) => {
                const account = DEMO_ACCOUNTS.find((a) => a.username === card.username);
                if (!account) return null;
                return (
                  <li key={card.username}>
                    <button
                      type="button"
                      onClick={() => fillDemo(account)}
                      className="lift glass-card flex h-full w-full flex-col gap-1 rounded-card p-3 text-left hover:bg-glass-fill-strong"
                    >
                      <card.icon className="size-5 text-coral" aria-hidden="true" />
                      <span className="text-14 font-medium text-cream">{card.label}</span>
                      <span className="font-mono text-11 text-muted-on-navy">{account.username}</span>
                      <span className="text-12 text-muted-on-navy">{card.note}</span>
                    </button>
                  </li>
                );
              })}
            </ul>
          </section>
        )}
      </div>
    </main>
  );
}
