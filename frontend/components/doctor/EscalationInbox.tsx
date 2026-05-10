"use client";

import { useEffect, useState } from "react";
import { getDoctorInbox } from "@/lib/api";

export function EscalationInbox() {
  const [rows, setRows] = useState<Array<Record<string, unknown>>>([]);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await getDoctorInbox();
        if (!cancelled) setRows(data);
      } catch (e) {
        if (!cancelled) setErr(String(e));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <section className="rounded-2xl border border-[var(--line)] bg-[var(--card)] p-4 shadow-sm">
      <h2 className="text-lg font-semibold">Escalated questions</h2>
      {err && <p className="mt-2 text-sm text-red-700">{err}</p>}
      <ul className="mt-4 space-y-3">
        {rows.map((r) => (
          <li key={String(r.id)} className="rounded-xl border border-[var(--line)] p-3 text-sm">
            <div className="font-semibold">{String(r.patient_id)}</div>
            <div className="mt-1 text-[var(--muted)]">{String(r.created_at ?? "")}</div>
            <div className="mt-2 whitespace-pre-wrap">{String(r.question ?? "")}</div>
          </li>
        ))}
        {rows.length === 0 && !err && (
          <li className="text-sm text-[var(--muted)]">No escalations yet.</li>
        )}
      </ul>
    </section>
  );
}
