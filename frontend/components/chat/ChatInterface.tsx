"use client";

import { useCallback, useState } from "react";
import { postChat } from "@/lib/api";
import type { UiLang } from "@/lib/i18n";
import { t } from "@/lib/i18n";
import { MessageList, type UiMessage } from "./MessageList";
import { VoiceInput } from "./VoiceInput";
import { extract_lab_hint } from "@/lib/labHint";

export function ChatInterface({
  patientId,
  lang,
  detailLevel,
}: {
  patientId: string;
  lang: UiLang;
  detailLevel: "full" | "basic";
}) {
  const [messages, setMessages] = useState<UiMessage[]>([
    {
      role: "assistant",
      text:
        lang === "es"
          ? "Puede hacer preguntas sobre sus notas guardadas. No sustituye el consejo médico."
          : "You can ask questions about your saved visit notes. This is not medical advice.",
    },
  ]);
  const [input, setInput] = useState("");
  const [typing, setTyping] = useState(false);

  const send = useCallback(async () => {
    const q = input.trim();
    if (!q) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", text: q }]);
    setTyping(true);
    try {
      const res = await postChat(patientId, q, {
        language: lang,
        detailLevel: detailLevel,
      });
      const trendName = extract_lab_hint(q) ?? "Lab trend";
      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          text: res.answer,
          citations: res.citations,
          trend: res.trend ?? undefined,
          trendName,
        },
      ]);
    } catch (e) {
      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          text: `Sorry — could not reach the API. (${String(e)})`,
        },
      ]);
    } finally {
      setTyping(false);
    }
  }, [detailLevel, input, lang, patientId]);

  return (
    <section className="rounded-2xl border border-[var(--line)] bg-[var(--card)] p-4 shadow-sm">
      <h2 className="text-lg font-semibold">{t(lang, "chat")}</h2>
      <div className="mt-4 max-h-[55vh] overflow-y-auto pr-1">
        <MessageList messages={messages} typing={typing} lang={lang} />
      </div>
      <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-end">
        <textarea
          className="min-h-[120px] w-full flex-1 rounded-xl border border-[var(--line)] bg-[var(--bg)] p-3 text-base"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={t(lang, "placeholder")}
        />
        <div className="flex flex-wrap gap-2">
          <VoiceInput lang={lang} onText={(text) => setInput((prev) => (prev ? `${prev} ${text}` : text))} />
          <button
            type="button"
            className="min-h-touch min-w-touch rounded-xl bg-blue-600 px-5 py-3 text-base font-semibold text-white"
            onClick={send}
            disabled={typing}
          >
            {t(lang, "send")}
          </button>
        </div>
      </div>
    </section>
  );
}
