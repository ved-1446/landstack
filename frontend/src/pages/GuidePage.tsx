import { PageHeader } from "../components/ui";
import { GuidePanel } from "../features/guide/GuidePanel";

/** /app/guide: the Land Guide as a full page (one nav tab; no floating button). Page polish comes in 13b. */
export default function GuidePage() {
  return (
    <section>
      <PageHeader eyebrow="LAND GUIDE" title="Ask in plain" emphasis="words" subtitle="General questions about land records, answered only from a small list of public pages. It never sees any plot." />
      <div className="mt-8">
        <GuidePanel variant="page" />
      </div>
    </section>
  );
}
