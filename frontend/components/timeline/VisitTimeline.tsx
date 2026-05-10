"use client";

import type { TimelineRow } from "@/lib/api";
import type { UiLang } from "@/lib/i18n";
import { t } from "@/lib/i18n";

export function VisitTimeline({ rows, lang }: { rows: TimelineRow[]; lang: UiLang }) {
  return (
    <section className="rounded-2xl border border-[var(--line)] bg-[var(--card)] p-4 shadow-sm">
      <h2 className="text-lg font-semibold">{t(lang, "timeline")}</h2>
      <ol className="mt-4 space-y-3">
        {rows.map((r) => (
          <li key={r.id} className="rounded-xl border border-[var(--line)] p-3">
            <div className="text-sm font-semibold text-blue-900">
              {r.visit_date ?? "Date unknown"} · {r.document_type ?? "note"}
            </div>
            <div className="mt-1 text-sm text-[var(--muted)]">{r.summary ?? r.chief_complaint ?? ""}</div>
            <div className="mt-1 text-xs text-[var(--muted)]">{r.provider_name ?? ""}</div>
          </li>
        ))}
      </ol>
    </section>
  );
}
