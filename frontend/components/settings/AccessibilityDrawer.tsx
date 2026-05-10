"use client";

import { useAccessibility } from "@/context/AccessibilityContext";
import type { UiLang } from "@/lib/i18n";
import { t } from "@/lib/i18n";

export function AccessibilityDrawer({ lang }: { lang: UiLang }) {
  const a = useAccessibility();
  return (
    <aside className="rounded-2xl border border-[var(--line)] bg-[var(--card)] p-4 shadow-sm">
      <h2 className="text-lg font-semibold">{t(lang, "settings")}</h2>
      <div className="mt-4 flex flex-col gap-4">
        <label className="flex min-h-touch items-center gap-3 text-base">
          <input
            type="checkbox"
            className="h-5 w-5"
            checked={a.dyslexiaFont}
            onChange={(e) => a.setDyslexiaFont(e.target.checked)}
          />
          <span>{t(lang, "dyslexiaFont")}</span>
        </label>
        <div>
          <div className="mb-2 font-medium">{t(lang, "fontSize")}</div>
          <div className="flex flex-wrap gap-2">
            {(["sm", "md", "lg"] as const).map((s) => (
              <button
                key={s}
                type="button"
                className={`min-h-touch min-w-touch rounded-xl border px-4 py-2 text-sm font-medium ${
                  a.fontSize === s ? "border-blue-600 bg-blue-50" : "border-[var(--line)]"
                }`}
                onClick={() => a.setFontSize(s)}
              >
                {s.toUpperCase()}
              </button>
            ))}
          </div>
        </div>
        <label className="flex min-h-touch items-center gap-3 text-base">
          <input
            type="checkbox"
            className="h-5 w-5"
            checked={a.offWhite}
            onChange={(e) => a.setOffWhite(e.target.checked)}
          />
          <span>{t(lang, "offWhite")}</span>
        </label>
        <label className="flex min-h-touch items-center gap-3 text-base">
          <input
            type="checkbox"
            className="h-5 w-5"
            checked={a.highContrast}
            onChange={(e) => a.setHighContrast(e.target.checked)}
          />
          <span>{t(lang, "highContrast")}</span>
        </label>
        <label className="flex min-h-touch items-center gap-3 text-base">
          <input
            type="checkbox"
            className="h-5 w-5"
            checked={a.voiceOutput}
            onChange={(e) => a.setVoiceOutput(e.target.checked)}
          />
          <span>{t(lang, "voiceToggle")}</span>
        </label>
      </div>
    </aside>
  );
}
