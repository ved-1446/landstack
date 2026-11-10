import { BadgeCheck, Copy, Download, FileX } from "lucide-react";
import { useEffect, useState } from "react";
import { ApiError, downloadPassportPdf, getPassport } from "../../api";
import { ErrorState } from "../../components/ErrorState";
import { Button, Chip, Drawer, EmptyState, EvidenceCard, Gauge, Skeleton, useToast } from "../../components/ui";
import { BAND_WORDS, prettyRole } from "../../constants";
import { useFetch } from "../../hooks";
import type { ConflictType, Passport } from "../../types";
import { UnusualChip } from "./UnusualChip";
import { VerifyDialog } from "./VerifyDialog";

interface PassportDrawerProps {
  ulpin: string;
  role: string;
  /** the rule text for each kind of conflict, from /conflict-types */
  rules: Partial<Record<ConflictType, string>>;
  /** the conflict types whose data is SIMULATED (shown with a visible "Simulated" chip) */
  simulatedTypes: ReadonlySet<ConflictType>;
  /** a passport that was already fetched (by the search box), so it is not fetched twice */
  prefetched: Passport | null;
  onClose: () => void;
  onLoaded: (passport: Passport) => void;
}

const sqm = (n: number) => `${Math.round(n).toLocaleString()} m²`;

function Fact({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <dt className="font-mono text-11 tracking-wider text-faint-on-cream">{label}</dt>
      <dd className="mt-1 text-14 font-medium text-ink">{children}</dd>
    </div>
  );
}

function RecordRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-3 border-t border-line-on-cream py-2 first:border-t-0">
      <dt className="text-13 text-muted-on-cream">{label}</dt>
      <dd className="text-right text-13 text-ink">{children}</dd>
    </div>
  );
}

/** A record that is not on file. Written out in words, never left blank. */
function Missing() {
  return (
    <span className="inline-flex items-center gap-1 font-semibold">
      <FileX className="size-4" aria-hidden="true" />
      Missing
    </span>
  );
}

function SheetSkeleton() {
  return (
    <div aria-label="Loading passport" role="status" className="rounded-card bg-cream p-4">
      <Skeleton on="cream" className="h-4 w-24" />
      <Skeleton on="cream" className="mt-3 h-10 w-48" />
      <Skeleton on="cream" className="mx-auto mt-6 h-32 w-56 rounded-pill" />
      <Skeleton on="cream" className="mt-6 h-16" />
      <Skeleton on="cream" className="mt-3 h-24" />
    </div>
  );
}

export function PassportDrawer({ ulpin, role, rules, simulatedTypes, prefetched, onClose, onLoaded }: PassportDrawerProps) {
  const toast = useToast();
  const [verifyOpen, setVerifyOpen] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const { data: passport, loading, error, retry } = useFetch(
    (signal) => (prefetched && prefetched.ulpin === ulpin ? Promise.resolve(prefetched) : getPassport(ulpin, signal)),
    [ulpin],
  );
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    if (passport) onLoaded(passport);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [passport]);

  // A 404 is shown as its own friendly state: the plot does not exist or is not the visitor's (the API answers the same for both).
  useEffect(() => {
    setNotFound(Boolean(error) && /No plot found/i.test(error ?? ""));
  }, [error]);

  async function download() {
    setDownloading(true);
    try {
      const blob = await downloadPassportPdf(ulpin);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `landpassport_${ulpin}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      toast.push({ title: "PDF passport downloaded", description: `landpassport_${ulpin}.pdf`, tone: "success" });
    } catch (err) {
      toast.push({
        title: "Could not download the PDF",
        description: err instanceof ApiError ? err.message : "Please try again.",
        tone: "error",
      });
    }
    setDownloading(false);
  }

  async function copyUlpin() {
    try {
      await navigator.clipboard.writeText(ulpin);
      toast.push({ title: "ULPIN copied", description: ulpin, tone: "success" });
    } catch {
      toast.push({ title: "Could not copy", description: "Select the ULPIN and copy it by hand.", tone: "error" });
    }
  }

  const total = passport ? passport.findings.reduce((sum, f) => sum + f.points, 0) : 0;
  const capped = passport ? total > passport.score : false;

  return (
    <>
      <Drawer open onClose={onClose} label="Land passport" viewingAs={prettyRole(role)}>
        {loading && !passport ? (
          <SheetSkeleton />
        ) : notFound ? (
          <EmptyState
            icon={FileX}
            title="Plot not found"
            description="This plot was not found, or it is not one of yours."
            action={
              <Button variant="secondary" onClick={onClose}>
                Close
              </Button>
            }
          />
        ) : error || !passport ? (
          <ErrorState message={error ?? "The passport could not be loaded."} onRetry={retry} />
        ) : (
          <>
            <article className="rounded-card bg-cream p-4 text-ink" aria-label={`Land passport for survey ${passport.survey_no}`}>
              <p className="font-mono text-11 tracking-wider text-faint-on-cream">LAND PASSPORT</p>
              <h2 className="mt-1 font-serif text-34 text-ink">Survey {passport.survey_no}</h2>
              <div className="mt-2 flex items-center gap-2">
                <Chip surface="cream">{passport.ulpin}</Chip>
                <button
                  type="button"
                  onClick={copyUlpin}
                  aria-label="Copy ULPIN"
                  className="flex size-8 items-center justify-center rounded-control text-muted-on-cream hover:bg-line-on-cream"
                >
                  <Copy className="size-4" aria-hidden="true" />
                </button>
              </div>

              <div className="mt-6">
                <Gauge score={passport.score} band={passport.band} />
              </div>
              <div className="mt-3 flex flex-col items-center gap-2 text-center">
                <Chip surface="cream" tone={passport.band}>
                  {BAND_WORDS[passport.band]}
                </Chip>
                <p className="text-13 text-muted-on-cream">
                  {passport.findings.length === 0
                    ? "No conflicts found."
                    : `${passport.findings.length} ${passport.findings.length === 1 ? "conflict" : "conflicts"} found.`}
                </p>
                {capped && <p className="text-13 text-muted-on-cream">Score is capped at 100.</p>}
                {passport.unusual?.flag && <UnusualChip unusual={passport.unusual} />}
              </div>

              <dl className="mt-6 grid grid-cols-2 gap-4 border-t border-line-on-cream pt-4">
                <Fact label="AREA">{passport.area_sqm === null ? "Not available" : sqm(passport.area_sqm)}</Fact>
                <Fact label="LAND USE">{passport.land_use}</Fact>
                <Fact label="OWNER (RoR)">{passport.ror ? passport.ror.owner_name : <Missing />}</Fact>
                <Fact label="VILLAGE">{passport.village}</Fact>
              </dl>

              {passport.findings.length > 0 && (
                <section aria-label="Conflicts" className="mt-6 space-y-2">
                  {passport.findings.map((finding, i) => (
                    <EvidenceCard
                      key={`${finding.type}-${i}`}
                      type={finding.type}
                      points={finding.points}
                      evidence={finding.evidence}
                      rule={rules[finding.type]}
                      simulated={simulatedTypes.has(finding.type)}
                    />
                  ))}
                </section>
              )}

              <section aria-label="Records on file" className="mt-6">
                <h3 className="mb-1 font-mono text-11 tracking-wider text-faint-on-cream">RECORDS ON FILE</h3>
                <dl>
                  <RecordRow label="Land record">
                    {passport.ror ? `${passport.ror.owner_name}, ${sqm(passport.ror.recorded_area_sqm)}` : <Missing />}
                  </RecordRow>
                  <RecordRow label="Registration">
                    {passport.registration ? `${passport.registration.owner_name}, ${passport.registration.registered_on}` : <Missing />}
                  </RecordRow>
                  <RecordRow label="Tax paid until">{passport.tax ? passport.tax.paid_until : <Missing />}</RecordRow>
                </dl>
              </section>
            </article>

            <div className="mt-4 flex flex-col gap-2">
              <Button onClick={download} loading={downloading}>
                <Download className="size-4" aria-hidden="true" />
                Download PDF passport
              </Button>
              <Button variant="secondary" onClick={() => setVerifyOpen(true)}>
                <BadgeCheck className="size-4" aria-hidden="true" />
                Verify
              </Button>
            </div>
          </>
        )}
      </Drawer>
      <VerifyDialog open={verifyOpen} onClose={() => setVerifyOpen(false)} />
    </>
  );
}
