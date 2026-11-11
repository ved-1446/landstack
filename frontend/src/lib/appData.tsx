import { createContext, useContext, type ReactNode } from "react";
import { getConflictTypes, getConflicts, getPlots, getSummary } from "../api";
import { useFetch } from "../hooks";
import type { ConflictRow, ConflictTypeInfo, PlotCollection, Role, Summary } from "../types";

type Loaded<T> = { data: T | null; loading: boolean; error: string | null; retry: () => void };

interface AppData {
  /** the plots this person may see (a citizen: their own) */
  plots: Loaded<PlotCollection>;
  /** staff only: counts and findings per type; for a citizen this stays null and is never requested */
  summary: Loaded<Summary | null>;
  /** staff only: every plot with findings */
  conflicts: Loaded<ConflictRow[] | null>;
  /** the rule text and the "simulated" flag of each kind of conflict */
  types: Loaded<ConflictTypeInfo[]>;
}

const Context = createContext<AppData | null>(null);

/**
 * Fetches the lists every role page needs ONCE when the signed-in area opens, and shares them, so moving between the dashboard,
 * the plots list and the conflicts page does not run the (about one second) scoring again each time.
 */
export function AppDataProvider({ role, children }: { role: Role; children: ReactNode }) {
  const staff = role !== "citizen";
  const plots = useFetch((signal) => getPlots({}, signal), []);
  const summary = useFetch<Summary | null>((signal) => (staff ? getSummary(signal) : Promise.resolve(null)), [staff]);
  const conflicts = useFetch<ConflictRow[] | null>((signal) => (staff ? getConflicts(signal) : Promise.resolve(null)), [staff]);
  const types = useFetch((signal) => getConflictTypes(signal), []);
  return <Context.Provider value={{ plots, summary, conflicts, types }}>{children}</Context.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAppData(): AppData {
  const value = useContext(Context);
  if (!value) throw new Error("useAppData must be used inside <AppDataProvider>");
  return value;
}
