// DEMO ONLY. These are the public demo logins from the README (never real credentials).
// The "Try a demo account" row on the login screen is shown unless VITE_DEMO_ACCOUNTS is "false".
// It MUST be "false" in any real deployment, because these passwords end up in the JavaScript bundle.
export const DEMO_ACCOUNTS_ENABLED = import.meta.env.VITE_DEMO_ACCOUNTS !== "false";

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
