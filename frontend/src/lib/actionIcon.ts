import { Download, FileSearch, MessageCircleQuestion, ShieldX, Sparkles, type LucideIcon } from "lucide-react";

/** The icon for an audit action (always shown next to its words, never on its own). */
export function actionIcon(action: string): LucideIcon {
  if (action.endsWith("_denied")) return ShieldX;
  if (action.endsWith("_not_found")) return FileSearch;
  if (action.startsWith("download")) return Download;
  if (action.startsWith("explain")) return Sparkles;
  if (action === "guide_ask") return MessageCircleQuestion;
  return FileSearch;
}
