// DEMO ONLY. These are the public demo logins from the README (never real credentials).
// The "Try a demo account" row on the login screen is shown ONLY when VITE_DEMO_ACCOUNTS is exactly "true" (off by default,
// because it shows demo usernames and passwords). Set it to "true" in frontend/.env for local demos, and in Vercel for the public DEMO
// site (the data is fake and the passwords are public on purpose). It MUST be "false" for anything with real data, because these
// passwords end up in the JavaScript bundle.
export const DEMO_ACCOUNTS_ENABLED = import.meta.env.VITE_DEMO_ACCOUNTS === "true";

export interface DemoAccount {
  username: string;
  password: string;
  role: string;
}

export const DEMO_ACCOUNTS: DemoAccount[] = [
  { username: "admin", password: "AdminDemo#2026", role: "Admin" },
  { username: "officer", password: "OfficerDemo#2026", role: "Officer" },
  { username: "citizen1", password: "Citizen1Demo#2026", role: "Citizen" },
  { username: "citizen2", password: "Citizen2Demo#2026", role: "Citizen" },
];
