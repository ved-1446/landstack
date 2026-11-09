import { useState, type ReactNode } from "react";
import { downloadPassportPdf, getPassport } from "../api";
import { BAND_COLOR, BAND_LABEL, BAND_TEXT, prettyType } from "../constants";
import { useFetch } from "../hooks";
import type { ConflictTypeInfo } from "../types";
import { ErrorMessage, Spinner } from "./Feedback";

interface Props {
  ulpin: string;
  conflictTypes: ConflictTypeInfo[] | null;
  onClose: () => void;
}

const sqm = (n: number) => `${Math.round(n).toLocaleString()} m²`;

function Missing() {
  return <span className="rounded bg-gray-200 px-2 py-0.5 text-sm font-semibold text-gray-800">Missing</span>;
}

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex justify-between gap-3 py-1 text-sm">
      <dt className="text-gray-500">{label}</dt>
      <dd className="text-right">{children}</dd>
    </div>
  );
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="border-t border-gray-200 px-4 py-3">
      <h3 className="mb-1 text-xs font-semibold uppercase text-gray-500">{title}</h3>
      {children}
    </section>
  );
}

export default function PassportPanel({ ulpin, conflictTypes, onClose }: Props) {
  const { data: p, loading, error, retry } = useFetch((signal) => getPassport(ulpin, signal), [ulpin]);
  const [pdf, setPdf] = useState<{ busy: boolean; error: string | null }>({ busy: false, error: null });

  // Fetch the PDF with the login token (api.ts), then save it as a file.
  async function downloadPdf() {
    setPdf({ busy: true, error: null });
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
      setPdf({ busy: false, error: null });
    } catch (err) {
      setPdf({ busy: false, error: err instanceof Error ? err.message : "Could not download the PDF." });
    }
  }

  return (
    <aside aria-label="Land passport"
           className="absolute bottom-0 right-0 top-0 z-10 w-96 max-w-full overflow-y-auto bg-white shadow-xl">
      <div className="flex items-start justify-between px-4 py-3">
        <div>
          <div className="text-xs uppercase text-gray-500">Land passport</div>
          <div className="font-mono text-lg font-semibold">{ulpin}</div>
        </div>
        <button type="button" onClick={onClose} aria-label="Close panel"
                className="rounded border border-gray-300 px-2 py-1 text-sm hover:bg-gray-100">
          Close ✕
        </button>
      </div>

      {loading && <div className="px-4 py-3"><Spinner label="Loading passport…" /></div>}
      {error && <div className="px-4 py-3"><ErrorMessage message={error} onRetry={retry} /></div>}

      {p && (
        <>
          <div className="flex items-center gap-3 px-4 pb-3">
            <span className="rounded px-3 py-1 text-2xl font-bold"
                  style={{ backgroundColor: BAND_COLOR[p.band], color: BAND_TEXT[p.band] }}>
              {p.score}
            </span>
            <div>
              <div className="text-sm font-semibold">{BAND_LABEL[p.band]} risk band</div>
              <div className="text-xs text-gray-500">Risk score out of 100</div>
            </div>
          </div>

          <div className="px-4 pb-3">
            <button type="button" onClick={downloadPdf} disabled={pdf.busy}
                    className="rounded border border-gray-300 px-3 py-1 text-sm hover:bg-gray-100 disabled:opacity-60">
              {pdf.busy ? "Preparing PDF…" : "Download PDF"}
            </button>
            {pdf.error && (
              <p role="alert" className="mt-2 rounded border border-red-300 bg-red-50 p-2 text-sm text-red-900">{pdf.error}</p>
            )}
          </div>

          <Section title="Plot">
            <dl>
              <Row label="Village">{p.village}</Row>
              <Row label="Land use">{p.land_use}</Row>
              <Row label="Survey number">{p.survey_no}</Row>
              <Row label="Mapped area">
                {p.area_sqm === null ? <span className="text-gray-600">Not available (invalid shape)</span> : sqm(p.area_sqm)}
              </Row>
            </dl>
          </Section>

          <Section title={`Findings (${p.findings.length})`}>
            {p.findings.length === 0 ? (
              <p className="text-sm text-gray-600">No conflicts found.</p>
            ) : (
              <ul className="space-y-2">
                {p.findings.map((f, i) => (
                  <li key={`${f.type}-${i}`} className="rounded border border-gray-200 p-2">
                    <div className="flex justify-between text-sm font-semibold">
                      <span title={conflictTypes?.find((t) => t.type === f.type)?.description}>
                        {prettyType(f.type)}
                      </span>
                      <span>+{f.points}</span>
                    </div>
                    <p className="mt-1 text-sm text-gray-700">{f.evidence}</p>
                  </li>
                ))}
              </ul>
            )}
          </Section>

          <Section title="Land record (RoR)">
            {p.ror ? (
              <dl>
                <Row label="Owner">{p.ror.owner_name}</Row>
                <Row label="Recorded area">{sqm(p.ror.recorded_area_sqm)}</Row>
              </dl>
            ) : <Missing />}
          </Section>

          <Section title="Registration">
            {p.registration ? (
              <dl>
                <Row label="Owner">{p.registration.owner_name}</Row>
                <Row label="Registered on">{p.registration.registered_on}</Row>
              </dl>
            ) : <Missing />}
          </Section>

          <Section title="Tax">
            {p.tax ? (
              <dl><Row label="Paid until">{p.tax.paid_until}</Row></dl>
            ) : <Missing />}
          </Section>
        </>
      )}
    </aside>
  );
}
