"use client";

import type { ChatCitation } from "@/lib/api";
import { CitationPill } from "./CitationPill";
import { TrendChart } from "./TrendChart";
import { speakText, stopSpeaking } from "@/lib/voice";
import { useAccessibility } from "@/context/AccessibilityContext";
import type { UiLang } from "@/lib/i18n";
import { t } from "@/lib/i18n";

export type UiMessage =
  | { role: "user"; text: string }
  | {
      role: "assistant";
      text: string;
      citations?: ChatCitation[];
      trend?: Array<Record<string, unknown>> | null;
      trendName?: string;
    };

export function MessageList({
  messages,
  typing,
  lang,
}: {
  messages: UiMessage[];
  typing: boolean;
  lang: UiLang;
}) {
  const a = useAccessibility();
  return (
    <div className="flex flex-col gap-4">
      {messages.map((m, idx) =>
        m.role === "user" ? (
          <div key={idx} className="self-end max-w-[90%] rounded-2xl bg-blue-600 px-4 py-3 text-white">
            {m.text}
          </div>
        ) : (
          <div
            key={idx}
            className="self-start max-w-[95%] rounded-2xl border border-[var(--line)] bg-[var(--card)] px-4 py-3"
          >
            <div className="whitespace-pre-wrap">{m.text}</div>
            {m.citations && m.citations.length > 0 && (
              <div className="mt-3">
                <div className="mb-2 text-sm font-semibold text-[var(--muted)]">{t(lang, "citations")}</div>
                <div className="flex flex-wrap gap-2">
                  {m.citations.map((c, i) => (
                    <CitationPill key={i} c={c} index={i} />
                  ))}
                </div>
              </div>
            )}
            {m.trend && m.trend.length > 0 && (
              <TrendChart data={m.trend} name={m.trendName ?? "Lab trend"} />
            )}
            {a.voiceOutput && (
              <div className="mt-3 flex gap-2">
                <button
                  type="button"
                  className="min-h-touch rounded-xl border border-[var(--line)] px-4 py-2 text-sm font-semibold"
                  onClick={() => speakText(m.text, lang === "es" ? "es-ES" : "en-US")}
                >
                  {t(lang, "voiceOut")}
                </button>
                <button
                  type="button"
                  className="min-h-touch rounded-xl border border-[var(--line)] px-4 py-2 text-sm font-semibold"
                  onClick={stopSpeaking}
                >
                  Stop
                </button>
              </div>
            )}
          </div>
        ),
      )}
      {typing && (
        <div className="text-sm text-[var(--muted)]" aria-live="polite">
          {t(lang, "typing")}
        </div>
      )}
    </div>
  );
}
