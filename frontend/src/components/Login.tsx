import { useState, type FormEvent } from "react";
import { login } from "../api";
import type { Session } from "../types";

interface Props {
  notice?: string | null; // e.g. "Your session has ended."
  onLoggedIn: (session: Session) => void;
}

export default function Login({ notice, onLoggedIn }: Props) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      onLoggedIn(await login(username.trim(), password));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not log in.");
      setBusy(false);
    }
  }

  return (
    <div className="flex h-full items-center justify-center p-6">
      <form onSubmit={submit} className="w-80 space-y-3 rounded border border-gray-300 bg-white p-5 shadow">
        <h1 className="text-lg font-semibold">LandStack</h1>
        <p className="text-sm text-gray-600">Log in to see land records (fake demo data).</p>
        {notice && <p role="status" className="rounded bg-yellow-100 p-2 text-sm text-yellow-900">{notice}</p>}

        <label className="block text-sm">
          Username
          <input value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username"
                 autoFocus required className="mt-1 w-full rounded border border-gray-300 px-2 py-1" />
        </label>
        <label className="block text-sm">
          Password
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)}
                 autoComplete="current-password" required
                 className="mt-1 w-full rounded border border-gray-300 px-2 py-1" />
        </label>

        {error && <p role="alert" className="rounded border border-red-300 bg-red-50 p-2 text-sm text-red-900">{error}</p>}

        <button type="submit" disabled={busy}
                className="w-full rounded bg-gray-800 px-3 py-2 text-white hover:bg-gray-900 disabled:opacity-60">
          {busy ? "Logging in…" : "Log in"}
        </button>
      </form>
    </div>
  );
}
