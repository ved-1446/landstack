import { Camera, Search } from "lucide-react";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { useNavigate } from "react-router";
import { Button, GlassCard, PageHeader } from "../../components/ui";
import { documentIdFrom, isUlpin } from "../../lib/format";
import { VerifyPanel } from "../VerifyPage";

// Chrome and Edge can read QR codes from the camera (BarcodeDetector); other browsers cannot, and then only pasting works.
interface Detector {
  detect: (source: CanvasImageSource) => Promise<{ rawValue: string }[]>;
}
type DetectorConstructor = new (options: { formats: string[] }) => Detector;
const Detector = (window as unknown as { BarcodeDetector?: DetectorConstructor }).BarcodeDetector;

/** Scan a QR code with the camera and hand back what it says. Stops the camera as soon as it has read something. */
function Scanner({ onRead, onClose }: { onRead: (text: string) => void; onClose: () => void }) {
  const video = useRef<HTMLVideoElement>(null);
  const [problem, setProblem] = useState<string | null>(null);

  useEffect(() => {
    let stream: MediaStream | null = null;
    let timer = 0;
    let stopped = false;
    (async () => {
      try {
        if (!Detector) throw new Error("This browser cannot read QR codes.");
        const detector = new Detector({ formats: ["qr_code"] });
        stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } });
        if (!video.current || stopped) return;
        video.current.srcObject = stream;
        await video.current.play();
        const look = async () => {
          if (stopped || !video.current) return;
          const found = await detector.detect(video.current).catch(() => []);
          if (found[0]) onRead(found[0].rawValue);
          else timer = window.setTimeout(look, 300);
        };
        void look();
      } catch (err) {
        setProblem(err instanceof Error && err.name !== "NotAllowedError" ? err.message : "The camera is not available or was not allowed. Paste the code instead.");
      }
    })();
    return () => {
      stopped = true;
      window.clearTimeout(timer);
      stream?.getTracks().forEach((track) => track.stop());
    };
  }, [onRead]);

  return (
    <div className="mt-4">
      {problem ? (
        <p role="alert" className="text-14 text-cream">
          {problem}
        </p>
      ) : (
        <video ref={video} muted playsInline aria-label="Camera view for scanning a QR code" className="aspect-video w-full max-w-md rounded-card bg-navy-950" />
      )}
      <Button variant="secondary" size="sm" className="mt-3" onClick={onClose}>
        Close the camera
      </Button>
    </div>
  );
}

/**
 * The citizen's Verify tab. Paste (or scan) what is on a printed passport: a document id or the QR code's web address checks that the paper is
 * still true. A plot id (14 letters and digits) opens that plot's passport page instead, if it is one of yours.
 */
export default function CitizenVerify() {
  const navigate = useNavigate();
  const [text, setText] = useState("");
  const [docId, setDocId] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [scanning, setScanning] = useState(false);
  const [round, setRound] = useState(0);

  function handle(raw: string) {
    const value = raw.trim();
    setMessage(null);
    if (!value) return;
    const asPlot = value.toUpperCase();
    if (isUlpin(asPlot)) {
      navigate(`/app/plots/${asPlot}`);
      return;
    }
    const id = documentIdFrom(value);
    if (!id) {
      setDocId(null);
      setMessage("That does not look like a plot id (14 letters and digits) or a document id like 7KQ2-M9XD-4TPA.");
      return;
    }
    setDocId(id);
    setRound((n) => n + 1);
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    handle(text);
  }

  return (
    <section>
      <PageHeader eyebrow="MY LAND" title="Check a" emphasis="passport" subtitle="Paste the document id printed on a land passport, or the web address in its QR code. Or type one of your plot ids to open its passport." />
      <GlassCard className="mt-8 max-w-3xl">
        <form onSubmit={submit} className="flex flex-wrap items-end gap-3">
          <div className="min-w-0 flex-1">
            <label htmlFor="verify-any" className="mb-2 block text-13 text-muted-on-navy">
              Document id, QR address or plot id
            </label>
            <input
              id="verify-any"
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="7KQ2-M9XD-4TPA or MH000100000001"
              autoComplete="off"
              spellCheck={false}
              className="h-11 w-full rounded-control border border-glass-border bg-navy-950 px-3 font-mono text-14 text-cream placeholder:text-faint-on-navy"
            />
          </div>
          <Button type="submit" disabled={!text.trim()}>
            <Search className="size-4" aria-hidden="true" />
            Check
          </Button>
          {Detector && (
            <Button type="button" variant="secondary" onClick={() => setScanning((v) => !v)}>
              <Camera className="size-4" aria-hidden="true" />
              Scan a QR code
            </Button>
          )}
        </form>
        {scanning && (
          <Scanner
            onRead={(read) => {
              setScanning(false);
              setText(read);
              handle(read);
            }}
            onClose={() => setScanning(false)}
          />
        )}
        <div aria-live="polite">{message && <p className="mt-4 text-14 text-cream">{message}</p>}</div>
      </GlassCard>
      {docId && (
        <div className="mt-6 max-w-3xl">
          <GlassCard>
            <VerifyPanel key={round} initialId={docId} />
          </GlassCard>
        </div>
      )}
    </section>
  );
}
