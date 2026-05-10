"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { getDoctorPatients, getTimeline } from "@/lib/api";
import type { TimelineRow } from "@/lib/api";
import { NoteIntake } from "@/components/doctor/NoteIntake";
import { EscalationInbox } from "@/components/doctor/EscalationInbox";

type PatientSummary = { patient_id: string; visit_count: number };

export default function DoctorPage() {
  const [patients, setPatients] = useState<PatientSummary[]>([]);
  const [timelines, setTimelines] = useState<Record<string, TimelineRow[]>>({});
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const ps = await getDoctorPatients();
        if (cancelled) return;
        setPatients(ps);
        const tl: Record<string, TimelineRow[]> = {};
        for (const p of ps) {
          tl[p.patient_id] = await getTimeline(p.patient_id);
        }
        if (!cancelled) setTimelines(tl);
      } catch (e) {
        if (!cancelled) setErr(String(e));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <main className="mx-auto max-w-5xl space-y-8 px-4 py-8">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold">Clinician view (demo)</h1>
        <Link href="/" className="min-h-touch rounded-xl border border-[var(--line)] px-4 py-2 text-sm font-semibold">
          Home
        </Link>
      </div>
      {err && <p className="text-sm text-red-700">{err}</p>}
      <NoteIntake />
      <section className="rounded-2xl border border-[var(--line)] bg-[var(--card)] p-4 shadow-sm">
        <h2 className="text-lg font-semibold">Demo patients</h2>
        <ul className="mt-4 space-y-4">
          {patients.map((p) => (
            <li key={p.patient_id} className="rounded-xl border border-[var(--line)] p-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="font-semibold">{p.patient_id}</div>
                <div className="text-sm text-[var(--muted)]">{p.visit_count} visits</div>
                <Link
                  href={`/patient/${encodeURIComponent(p.patient_id)}`}
                  className="min-h-touch rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white"
                >
                  Open patient view
                </Link>
              </div>
              <ul className="mt-3 space-y-2 text-sm">
                {(timelines[p.patient_id] ?? []).map((v) => (
                  <li key={v.id} className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-black/5 p-2">
                    <span>
                      {v.visit_date ?? "unknown date"} · {v.document_type ?? "note"}
                    </span>
                    <button
                      type="button"
                      className="min-h-touch rounded-lg border border-[var(--line)] px-3 py-2 text-xs font-semibold"
                      onClick={() => window.alert("Demo only: no message was sent.")}
                    >
                      Approve & send to patient
                    </button>
                  </li>
                ))}
              </ul>
            </li>
          ))}
        </ul>
      </section>
      <EscalationInbox />
    </main>
  );
}
