import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { Send, Sparkles, Mic, MicOff, Paperclip, MessageSquarePlus, BookOpen, Volume2, Square } from "lucide-react";
import { toast } from "sonner";
import TranslateButton from "@/components/TranslateButton";
import { useUiI18n } from "@/lib/ui-i18n";

const SUGGESTIONS = [
  "Explain my latest report simply",
  "Summarize my last visit",
  "What changed in my latest labs?",
  "What does my medication do?",
];
const THINKING_STEPS = [
  "Reviewing your question...",
  "Finding relevant records...",
  "Drafting a clear summary...",
];
const VOICE_LANG_MAP = {
  en: "en-US",
  es: "es-ES",
  fr: "fr-FR",
  de: "de-DE",
  zh: "zh-CN",
  ja: "ja-JP",
  ko: "ko-KR",
};

export default function AIAssistant() {
  const { language: selectedLanguage, t } = useUiI18n();
  const [me, setMe] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [thinking, setThinking] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [recording, setRecording] = useState(false);
  const [playingId, setPlayingId] = useState(null);
  const [openCitationByMsg, setOpenCitationByMsg] = useState({});
  const [thinkingStepIdx, setThinkingStepIdx] = useState(0);
  const scrollRef = useRef(null);
  const recognitionRef = useRef(null);
  const requestControllerRef = useRef(null);

  useEffect(() => {
    api.get("/patients").then((r) => setMe(r.data?.[0]));
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, thinking]);

  useEffect(() => {
    if (!thinking) {
      setThinkingStepIdx(0);
      return undefined;
    }
    const t = setInterval(() => {
      setThinkingStepIdx((v) => (v + 1) % THINKING_STEPS.length);
    }, 2200);
    return () => clearInterval(t);
  }, [thinking]);

  const normalizeReply = (replyRaw, sourceRaw) => {
    let cleanReply = replyRaw || "";
    let sources = Array.isArray(sourceRaw) ? sourceRaw : [];

    const trimmed = cleanReply.trim();
    const maybeJson = trimmed
      .replace(/^```json\s*/i, "")
      .replace(/^```\s*/i, "")
      .replace(/\s*```$/, "");
    if (maybeJson.startsWith("{") && maybeJson.includes("\"answer\"")) {
      try {
        const obj = JSON.parse(maybeJson);
        if (typeof obj.answer === "string" && obj.answer.trim()) {
          cleanReply = obj.answer.trim();
        }
        if ((!sources || sources.length === 0) && Array.isArray(obj.citations)) {
          sources = obj.citations.slice(0, 4).map((c, i) => ({
            id: `c${i + 1}`,
            index: i + 1,
            label: `[${i + 1}]`,
            document_id: c.document_id || null,
            visit_date: c.visit_date || "unknown date",
            excerpt: c.chunk_excerpt || c.chunk_text || "",
          }));
        }
      } catch {
        // Keep raw reply as-is if JSON parse fails.
      }
    }
    return { cleanReply, sources };
  };

  const send = async (text) => {
    if (!text.trim() || !me || thinking) return;
    setInput("");
    const userMsg = { id: Date.now() + "u", role: "user", text };
    setMessages((m) => [...m, userMsg]);
    setThinking(true);
    const controller = new AbortController();
    requestControllerRef.current = controller;
    try {
      const r = await api.post(
        "/ai/chat",
        {
          patient_id: me.id,
          session_id: sessionId,
          text,
          language: selectedLanguage,
          input_language: selectedLanguage,
        },
        { signal: controller.signal },
      );
      setSessionId(r.data.session_id);
      const { cleanReply, sources } = normalizeReply(r.data.reply, r.data.sources);
      const aiMsg = { id: Date.now() + "a", role: "ai", text: cleanReply, sources };
      setMessages((m) => [...m, aiMsg]);
    } catch (e) {
      if (e?.code === "ERR_CANCELED") {
        setMessages((m) => [...m, { id: Date.now() + "a", role: "ai", text: t("Response stopped.") }]);
      } else {
        setMessages((m) => [...m, { id: Date.now() + "a", role: "ai", text: t("Sorry, I couldn't reach the assistant. Please try again.") }]);
      }
    } finally {
      requestControllerRef.current = null;
      setThinking(false);
    }
  };

  const stopGeneration = () => {
    if (requestControllerRef.current) {
      requestControllerRef.current.abort();
      requestControllerRef.current = null;
    }
    setThinking(false);
  };

  const startRecording = async () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      toast.error(t("Speech recognition is not supported in this browser."));
      return;
    }

    try {
      const recognition = new SpeechRecognition();
      recognition.lang = VOICE_LANG_MAP[selectedLanguage] || (navigator.language || "en-US");
      recognition.interimResults = false;
      recognition.continuous = false;

      recognition.onstart = () => setRecording(true);

      recognition.onresult = async (event) => {
        const text = event?.results?.[0]?.[0]?.transcript?.trim() || "";
        if (!text) {
          toast.error(t("Couldn't catch that. Please try again."));
          return;
        }
        await send(text);
      };

      recognition.onerror = () => {
        toast.error(t("Voice input failed. Please try again."));
      };

      recognition.onend = () => setRecording(false);

      recognitionRef.current = recognition;
      recognition.start();
    } catch {
      setRecording(false);
      toast.error(t("Microphone access denied or unavailable."));
    }
  };

  const stopRecording = () => {
    if (recognitionRef.current) {
      recognitionRef.current.stop();
    }
    setRecording(false);
  };

  const speakMessage = (msg) => {
    if (!window.speechSynthesis) {
      toast.error(t("Text-to-speech is not supported in this browser."));
      return;
    }

    if (playingId === msg.id) {
      window.speechSynthesis.cancel();
      setPlayingId(null);
      return;
    }

    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(msg.text || "");
    utterance.lang = navigator.language || "en-US";
    utterance.onstart = () => setPlayingId(msg.id);
    utterance.onend = () => setPlayingId(null);
    utterance.onerror = () => {
      setPlayingId(null);
      toast.error(t("Couldn't play audio"));
    };
    window.speechSynthesis.speak(utterance);
  };

  const toggleCitation = (msgId, idx) => {
    setOpenCitationByMsg((prev) => ({
      ...prev,
      [msgId]: prev[msgId] === idx ? null : idx,
    }));
  };

  return (
    <div className="grid lg:grid-cols-4 gap-6 h-[calc(100vh-150px)]">
      <aside className="card-soft p-5 hidden lg:flex flex-col">
        <div className="flex items-center gap-2 mb-4">
          <BookOpen className="w-5 h-5 text-[#5BB9A6]" />
          <h3 className="font-[Outfit] text-lg font-semibold text-[#2F5D57]">{t("Chat history")}</h3>
        </div>
        <button data-testid="new-chat-button" onClick={() => { setMessages([]); setSessionId(null); }}
                className="flex items-center gap-2 px-3 py-2 rounded-xl bg-[#5BB9A6] text-white text-sm font-medium hover:bg-[#4AA391] transition-colors">
          <MessageSquarePlus className="w-4 h-4" /> {t("New chat")}
        </button>
        <div className="mt-4 space-y-2 overflow-y-auto flex-1 -mx-2 px-2">
          {[
            "About my Vitamin D level",
            "Understanding my HbA1c",
            "Side effects to expect",
            "Reading my MRI report",
          ].map((t, i) => (
            <div key={i} className="p-3 rounded-xl bg-[#F7FFFD] text-sm text-[#2F5D57] hover:bg-[#A7E3D4]/40 cursor-pointer truncate">
              {t}
            </div>
          ))}
        </div>
        <div className="mt-4 text-[10px] text-[#4B7A73] leading-relaxed">
          {t("AI provides educational information only. It does not diagnose or replace professional advice.")}
        </div>
      </aside>

      <main className="card-soft p-0 lg:col-span-3 flex flex-col overflow-hidden">
        <header className="px-6 py-4 border-b border-[#C2EBE1]/60 flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-[#5BB9A6] flex items-center justify-center">
            <Sparkles className="w-5 h-5 text-white" />
          </div>
          <div className="flex-1">
            <div className="font-[Outfit] font-semibold text-[#2F5D57]">MyHealthVoice AI</div>
            <div className="text-xs text-[#4B7A73]">{t("Speaks your language · educational only")}</div>
          </div>
        </header>

        <div ref={scrollRef} className="flex-1 overflow-y-auto p-6 space-y-4">
          {messages.length === 0 && (
            <div className="text-center py-10">
              <div className="inline-flex w-16 h-16 rounded-2xl bg-[#A7E3D4]/40 items-center justify-center">
                <Sparkles className="w-7 h-7 text-[#5BB9A6]" />
              </div>
              <h3 className="mt-4 font-[Outfit] text-2xl font-bold text-[#2F5D57]">{t("How can I help you today?")}</h3>
              <p className="text-sm text-[#4B7A73] mt-1">{t("Type or tap the mic — I'll reply in the language you use.")}</p>
              <div className="mt-6 flex flex-wrap gap-2 justify-center">
                {SUGGESTIONS.map((s) => (
                  <button key={s} data-testid={`suggestion-${s.replace(/\s+/g, "-").toLowerCase()}`}
                          onClick={() => send(s)}
                          disabled={thinking}
                          className="px-4 py-2 rounded-full bg-[#F7FFFD] border border-[#A7E3D4] text-sm text-[#2F5D57] hover:bg-[#D9F5EF] transition-colors">
                    {t(s)}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((m) => (
            <div key={m.id} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"} animate-fade-up`}>
              <div className={`max-w-[78%] p-4 shadow-sm ${
                m.role === "user"
                  ? "bg-[#5BB9A6] text-white rounded-2xl rounded-tr-sm"
                  : "bg-[#F7FFFD] border border-[#C2EBE1] text-[#1A332F] rounded-2xl rounded-tl-sm"
              }`}>
                <div className="text-sm leading-relaxed whitespace-pre-wrap">{m.text}</div>
                {m.role === "ai" && <TranslateButton text={m.text} />}
                {m.role === "ai" && (
                  <button data-testid={`speak-${m.id}`} onClick={() => speakMessage(m)}
                          className="mt-2 inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-[#A7E3D4]/40 hover:bg-[#A7E3D4]/70 text-[#2F5D57] text-xs font-medium transition-colors">
                    {playingId === m.id ? <><Square className="w-3 h-3" /> Stop</> : <><Volume2 className="w-3 h-3" /> Listen</>}
                  </button>
                )}
                {Array.isArray(m.sources) && m.sources.length > 0 && (
                  <div className="mt-2">
                    <div className="inline-flex flex-wrap gap-1.5">
                      {m.sources.map((s, i) => {
                        const idx = i + 1;
                        const label = typeof s === "string" ? `[${idx}]` : (s.label || `[${idx}]`);
                        return (
                          <button
                            key={`${m.id}-c-${idx}`}
                            onClick={() => toggleCitation(m.id, idx)}
                            className="text-[10px] px-2 py-0.5 rounded-full bg-[#A7E3D4]/30 hover:bg-[#A7E3D4]/60 text-[#2F5D57]"
                        title={t("Show source excerpt")}
                          >
                            {label}
                          </button>
                        );
                      })}
                    </div>
                    {openCitationByMsg[m.id] && (
                      <div className="mt-2 text-[11px] p-2 rounded-lg bg-[#F1FBF8] border border-[#C2EBE1] text-[#2F5D57]">
                        {(() => {
                          const selected = m.sources[openCitationByMsg[m.id] - 1];
                          if (!selected || typeof selected === "string") return selected || "No source details.";
                          const date = selected.visit_date ? ` (${selected.visit_date})` : "";
                          const doc = selected.document_id ? `Doc ${selected.document_id.slice(0, 8)}${date}` : `Source${date}`;
                          return `${doc}: ${selected.excerpt || "No excerpt available."}`;
                        })()}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))}

          {thinking && (
            <div className="flex justify-start">
              <div className="bg-[#F7FFFD] border border-[#C2EBE1] rounded-2xl rounded-tl-sm p-4">
                <div className="text-xs text-[#4B7A73] mb-1">{t(THINKING_STEPS[thinkingStepIdx])}</div>
                <span className="typing-dot" /><span className="typing-dot" /><span className="typing-dot" />
              </div>
            </div>
          )}
        </div>

        <div className="border-t border-[#C2EBE1]/60 p-4">
          <div className="flex items-end gap-2">
            <button data-testid="attach-button" className="w-10 h-10 rounded-xl bg-[#F7FFFD] hover:bg-[#A7E3D4]/40 flex items-center justify-center text-[#4B7A73] transition-colors">
              <Paperclip className="w-4 h-4" />
            </button>
            <button data-testid="voice-button" onClick={recording ? stopRecording : startRecording}
                    className={`w-10 h-10 rounded-xl flex items-center justify-center transition-colors ${
                      recording ? "bg-[#E05A5A] text-white animate-pulse" : "bg-[#F7FFFD] hover:bg-[#A7E3D4]/40 text-[#4B7A73]"
                    }`}>
              {recording ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
            </button>
            <textarea
              data-testid="ai-chat-input"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey && !thinking) { e.preventDefault(); send(input); } }}
              rows={1}
              placeholder={recording ? "Listening…" : "Ask anything about your health…"}
              className="flex-1 resize-none p-3 rounded-xl bg-[#F7FFFD] border border-[#C2EBE1] text-sm focus:outline-none focus:ring-2 focus:ring-[#5BB9A6]/40 max-h-32"
            />
            {!thinking ? (
              <button data-testid="send-message-button" onClick={() => send(input)} disabled={!input.trim()}
                      className="w-10 h-10 rounded-xl bg-[#5BB9A6] hover:bg-[#4AA391] flex items-center justify-center text-white transition-colors disabled:opacity-50">
                <Send className="w-4 h-4" />
              </button>
            ) : (
              <button data-testid="stop-message-button" onClick={stopGeneration}
                      className="w-10 h-10 rounded-xl bg-[#E05A5A] hover:bg-[#c64b4b] flex items-center justify-center text-white transition-colors">
                <Square className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
