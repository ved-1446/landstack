import { useAuth } from "../auth";
import { PageHeader } from "../components/ui";
import MapScreen from "../screens/MapScreen";

/** /app/map: the map screen inside the shell, as a framed card under the page header (never the page background). */
export default function MapPage() {
  const { session } = useAuth();
  if (!session) return null;
  return (
    <section>
      <PageHeader
        eyebrow={session.role === "citizen" ? "MY LAND" : "OFFICER WORK DESK"}
        title="Plots on the"
        emphasis="map"
        subtitle={session.role === "citizen" ? "Your plots, coloured by risk. Open one to see its passport." : "Every plot, coloured by risk. Search a plot id or click a plot to open its passport."}
      />
      <MapScreen session={session} />
    </section>
  );
}
