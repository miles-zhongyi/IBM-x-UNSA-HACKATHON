"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import {
  configureApiBase,
  getApiBase,
  getDiagnoses,
  getLabs,
  getMedications,
  getTimeline,
  ingestDocumentText,
  postEscalate,
} from "@/lib/api";
import type { TimelineRow } from "@/lib/api";
import type { UiLang } from "@/lib/i18n";
import { t } from "@/lib/i18n";
import { VisitTimeline } from "@/components/timeline/VisitTimeline";
import { DiagnosesPanel } from "@/components/panels/DiagnosesPanel";
import { MedicationsPanel } from "@/components/panels/MedicationsPanel";
import { LabsPanel } from "@/components/panels/LabsPanel";
import { ChatInterface } from "@/components/chat/ChatInterface";
import { AccessibilityDrawer } from "@/components/settings/AccessibilityDrawer";

const DEMO_IDS = ["marcus-demo", "elena-demo", "dorothy-demo"] as const;

export default function PatientDashboard({ patientId }: { patientId: string }) {
  const [lang, setLang] = useState<UiLang>("en");
  const [detail, setDetail] = useState<"full" | "basic">("full");
  const [apiField, setApiField] = useState(getApiBase());
  const [paste, setPaste] = useState("");
  const [ingestMsg, setIngestMsg] = useState<string | null>(null);
  const [timeline, setTimeline] = useState<TimelineRow[]>([]);
  const [dx, setDx] = useState<Array<Record<string, unknown>>>([]);
  const [meds, setMeds] = useState<Array<Record<string, unknown>>>([]);
  const [labs, setLabs] = useState<Array<Record<string, unknown>>>([]);
  const [escalateQ, setEscalateQ] = useState("");
  const [escalateStatus, setEscalateStatus] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [tl, d, m, l] = await Promise.all([
          getTimeline(patientId),
          getDiagnoses(patientId, false),
          getMedications(patientId),
          getLabs(patientId),
        ]);
        if (!cancelled) {
          setTimeline(tl);
          setDx(d);
          setMeds(m);
          setLabs(l);
        }
      } catch {
        if (!cancelled) {
          setTimeline([]);
          setDx([]);
          setMeds([]);
          setLabs([]);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [patientId]);

  const summary = useMemo(() => {
    const last = timeline[0];
    return {
      visits: timeline.length,
      lastDate: last?.visit_date ?? null,
      lastSummary: last?.summary ?? null,
    };
  }, [timeline]);

  async function ingestPaste() {
    setIngestMsg(null);
    try {
      const res = await ingestDocumentText(patientId, paste, "patient_paste");
      setIngestMsg(JSON.stringify(res, null, 2));
      setTimeline(await getTimeline(patientId));
    } catch (e) {
      setIngestMsg(String(e));
    }
  }

  async function escalate() {
    setEscalateStatus(null);
    try {
      const r = await postEscalate(patientId, escalateQ || "Patient requested help", "patient_ui");
      setEscalateStatus(`Ticket ${r.ticket_id} queued.`);
      setEscalateQ("");
    } catch (e) {
      setEscalateStatus(String(e));
    }
  }

  return (
    <main className="mx-auto max-w-6xl space-y-8 px-4 py-8">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">{patientId}</h1>
          <p className="text-sm text-[var(--muted)]">{t(lang, "onboardingHint")}</p>
        </div>
        <Link href="/" className="min-h-touch rounded-xl border border-[var(--line)] px-4 py-2 text-sm font-semibold">
          {t(lang, "backHome")}
        </Link>
      </div>

      <section className="rounded-2xl border border-[var(--line)] bg-[var(--card)] p-4 shadow-sm">
        <h2 className="text-lg font-semibold">{t(lang, "onboardingTitle")}</h2>
        <div className="mt-3 grid gap-3 md:grid-cols-2">
          <div>
            <div className="text-sm font-medium">{t(lang, "apiBase")}</div>
            <input
              className="mt-1 w-full rounded-xl border border-[var(--line)] bg-[var(--bg)] p-3 text-sm"
              value={apiField}
              onChange={(e) => setApiField(e.target.value)}
              onBlur={() => configureApiBase(apiField)}
            />
          </div>
          <div className="flex flex-wrap gap-2 items-end">
            {DEMO_IDS.map((id) => (
              <Link
                key={id}
                href={`/patient/${id}`}
                className="min-h-touch rounded-xl border border-[var(--line)] px-3 py-2 text-sm font-semibold"
              >
                {id === "marcus-demo" ? t(lang, "demoMarcus") : id === "elena-demo" ? t(lang, "demoElena") : t(lang, "demoDorothy")}
              </Link>
            ))}
          </div>
        </div>
        <label className="mt-4 block text-sm font-medium">
          Paste a note (50+ chars)
          <textarea
            className="mt-1 min-h-[120px] w-full rounded-xl border border-[var(--line)] bg-[var(--bg)] p-3 text-sm"
            value={paste}
            onChange={(e) => setPaste(e.target.value)}
          />
        </label>
        <button
          type="button"
          className="mt-3 min-h-touch rounded-xl bg-blue-600 px-5 py-3 text-sm font-semibold text-white"
          onClick={ingestPaste}
        >
          {t(lang, "pasteIngest")}
        </button>
        {ingestMsg && <pre className="mt-3 max-h-48 overflow-auto rounded-xl bg-black/5 p-3 text-xs">{ingestMsg}</pre>}
      </section>

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="rounded-2xl border border-[var(--line)] bg-[var(--card)] p-4 shadow-sm lg:col-span-3">
          <h2 className="text-lg font-semibold">Visit summary</h2>
          <p className="mt-2 text-sm text-[var(--muted)]">
            {summary.visits} saved visits · last visit date: {String(summary.lastDate ?? "—")}
          </p>
          <p className="mt-2 text-sm">{summary.lastSummary ?? ""}</p>
        </div>

        <div className="space-y-4 lg:col-span-1">
          <div className="rounded-2xl border border-[var(--line)] bg-[var(--card)] p-4 shadow-sm">
            <div className="text-sm font-semibold">{t(lang, "language")}</div>
            <div className="mt-2 flex gap-2">
              <button
                type="button"
                className={`min-h-touch flex-1 rounded-xl border px-3 py-2 text-sm font-semibold ${lang === "en" ? "border-blue-600 bg-blue-50" : "border-[var(--line)]"}`}
                onClick={() => setLang("en")}
              >
                English
              </button>
              <button
                type="button"
                className={`min-h-touch flex-1 rounded-xl border px-3 py-2 text-sm font-semibold ${lang === "es" ? "border-blue-600 bg-blue-50" : "border-[var(--line)]"}`}
                onClick={() => setLang("es")}
              >
                Español
              </button>
            </div>
            <div className="mt-4 text-sm font-semibold">Detail</div>
            <div className="mt-2 flex flex-col gap-2">
              <button
                type="button"
                className={`min-h-touch rounded-xl border px-3 py-2 text-left text-sm font-semibold ${detail === "full" ? "border-blue-600 bg-blue-50" : "border-[var(--line)]"}`}
                onClick={() => setDetail("full")}
              >
                {t(lang, "detailFull")}
              </button>
              <button
                type="button"
                className={`min-h-touch rounded-xl border px-3 py-2 text-left text-sm font-semibold ${detail === "basic" ? "border-blue-600 bg-blue-50" : "border-[var(--line)]"}`}
                onClick={() => setDetail("basic")}
              >
                {t(lang, "detailBasic")}
              </button>
            </div>
          </div>
          <AccessibilityDrawer lang={lang} />
          <div className="rounded-2xl border border-[var(--line)] bg-[var(--card)] p-4 shadow-sm">
            <div className="text-sm font-semibold">{t(lang, "escalate")}</div>
            <textarea
              className="mt-2 min-h-[80px] w-full rounded-xl border border-[var(--line)] bg-[var(--bg)] p-2 text-sm"
              value={escalateQ}
              onChange={(e) => setEscalateQ(e.target.value)}
              placeholder="What do you want a clinician to review?"
            />
            <button
              type="button"
              className="mt-2 min-h-touch w-full rounded-xl bg-amber-600 px-4 py-2 text-sm font-semibold text-white"
              onClick={escalate}
            >
              {t(lang, "escalate")}
            </button>
            {escalateStatus && <p className="mt-2 text-xs text-[var(--muted)]">{escalateStatus}</p>}
          </div>
        </div>

        <div className="space-y-4 lg:col-span-2">
          <VisitTimeline rows={timeline} lang={lang} />
          <div className="grid gap-4 md:grid-cols-2">
            <DiagnosesPanel rows={dx} lang={lang} />
            <MedicationsPanel rows={meds} lang={lang} />
          </div>
          <LabsPanel rows={labs} lang={lang} />
          <ChatInterface patientId={patientId} lang={lang} detailLevel={detail} />
        </div>
      </div>
    </main>
  );
}
