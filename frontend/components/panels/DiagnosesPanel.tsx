"use client";

import type { UiLang } from "@/lib/i18n";
import { t } from "@/lib/i18n";

export function DiagnosesPanel({
  rows,
  lang,
}: {
  rows: Array<Record<string, unknown>>;
  lang: UiLang;
}) {
  return (
    <section className="rounded-2xl border border-[var(--line)] bg-[var(--card)] p-4 shadow-sm">
      <h2 className="text-lg font-semibold">{t(lang, "diagnoses")}</h2>
      <ul className="mt-3 space-y-2 text-sm">
        {rows.slice(0, 20).map((r, i) => (
          <li key={i} className="rounded-lg border border-[var(--line)] p-2">
            <div className="font-medium">{String(r.name ?? "")}</div>
            <div className="text-xs text-[var(--muted)]">
              {String(r.status ?? "")} {r.visit_date ? `· ${String(r.visit_date)}` : ""}
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
