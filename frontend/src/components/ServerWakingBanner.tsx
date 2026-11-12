import { Hourglass, RefreshCw } from "lucide-react";
import { useState } from "react";
import { pingServer } from "../lib/ping";
import { useServerPhase } from "../lib/serverState";
import { Button } from "./ui";

/**
 * A small note at the bottom of the screen while the (free) API server is starting. It says what is happening in plain words, so
 * nobody thinks the site is broken, and the app keeps trying by itself. If two minutes pass with no answer it says so and offers a
 * "Try again" button. It never shows once the server has answered.
 */
export function ServerWakingBanner() {
  const phase = useServerPhase();
  const [checking, setChecking] = useState(false);
  if (phase === "ok") return null;

  async function tryAgain() {
    setChecking(true);
    const up = await pingServer();
    setChecking(false);
    if (up) window.location.reload(); // start clean now that it is up
  }

  return (
    <div role="status" aria-live="polite" className="fixed inset-x-0 bottom-(--edge) z-toast flex justify-center px-(--edge)">
      <div className="glass flex max-w-xl flex-wrap items-center gap-3 rounded-panel px-4 py-3 shadow-2">
        <Hourglass className="size-5 shrink-0 text-cream" aria-hidden="true" />
        {phase === "waking" ? (
          <p className="text-14 text-cream">
            <strong className="font-medium">The demo server is waking up.</strong> This can take about a minute the first time. LandStack keeps trying by itself.
          </p>
        ) : (
          <>
            <p className="text-14 text-cream">
              <strong className="font-medium">The demo server is still not answering.</strong> It may be down, or very slow to start.
            </p>
            <Button variant="secondary" size="sm" onClick={() => void tryAgain()} loading={checking}>
              <RefreshCw className="size-4" aria-hidden="true" />
              Try again
            </Button>
          </>
        )}
      </div>
    </div>
  );
}
