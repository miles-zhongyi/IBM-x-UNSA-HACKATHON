"use client";

import { useCallback, useRef, useState } from "react";
import { startRecognition } from "@/lib/voice";
import type { UiLang } from "@/lib/i18n";
import { t } from "@/lib/i18n";

export function VoiceInput({
  lang,
  onText,
}: {
  lang: UiLang;
  onText: (text: string) => void;
}) {
  const [listening, setListening] = useState(false);
  const stopRef = useRef<(() => void) | null>(null);

  const stop = useCallback(() => {
    stopRef.current?.();
    stopRef.current = null;
    setListening(false);
  }, []);

  const start = useCallback(() => {
    stop();
    setListening(true);
    const langTag = lang === "es" ? "es-ES" : "en-US";
    stopRef.current = startRecognition(
      {
        onResult: (text) => {
          onText(text);
          stop();
        },
        onError: () => stop(),
        onEnd: () => setListening(false),
      },
      langTag,
    );
    if (!stopRef.current) {
      setListening(false);
    }
  }, [lang, onText, stop]);

  return (
    <button
      type="button"
      className="min-h-touch min-w-touch rounded-xl border border-[var(--line)] bg-[var(--card)] px-4 py-2 text-sm font-semibold"
      onClick={() => (listening ? stop() : start())}
      aria-pressed={listening}
    >
      {listening ? "…" : t(lang, "voiceIn")}
    </button>
  );
}
