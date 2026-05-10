import { useEffect, useRef, useState } from "react";
import { api, API } from "@/lib/api";
import axios from "axios";
import { Send, Sparkles, Mic, MicOff, Paperclip, MessageSquarePlus, BookOpen, Volume2, Square } from "lucide-react";
import { toast } from "sonner";

const SUGGESTIONS = [
  "Explain my latest report simply",
  "Summarize my last visit",
  "What changed in my latest labs?",
  "What does my medication do?",
];

export default function AIAssistant() {
  const [me, setMe] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [thinking, setThinking] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [recording, setRecording] = useState(false);
  const [transcribing, setTranscribing] = useState(false);
  const [playingId, setPlayingId] = useState(null);
  const scrollRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);
  const audioRef = useRef(null);

  useEffect(() => {
    api.get("/patients").then((r) => setMe(r.data?.[0]));
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, thinking]);

  const send = async (text) => {
    if (!text.trim() || !me) return;
    setInput("");
    const userMsg = { id: Date.now() + "u", role: "user", text };
    setMessages((m) => [...m, userMsg]);
    setThinking(true);
    try {
      const r = await api.post("/ai/chat", { patient_id: me.id, session_id: sessionId, text });
      setSessionId(r.data.session_id);
      const aiMsg = { id: Date.now() + "a", role: "ai", text: r.data.reply, sources: r.data.sources };
      setMessages((m) => [...m, aiMsg]);
    } catch {
      setMessages((m) => [...m, { id: Date.now() + "a", role: "ai", text: "Sorry, I couldn't reach the assistant. Please try again." }]);
    } finally {
      setThinking(false);
    }
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mr = new MediaRecorder(stream, { mimeType: "audio/webm" });
      chunksRef.current = [];
      mr.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data); };
      mr.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        if (blob.size === 0) return;
        setTranscribing(true);
        try {
          const fd = new FormData();
          fd.append("file", blob, "voice.webm");
          const r = await axios.post(`${API}/voice/transcribe`, fd, { headers: { "Content-Type": "multipart/form-data" } });
          const text = (r.data.text || "").trim();
          if (text) {
            await send(text);
          } else {
            toast.error("Couldn't catch that. Please try again.");
          }
        } catch (e) {
          toast.error("Transcription failed");
        } finally {
          setTranscribing(false);
        }
      };
      mr.start();
      mediaRecorderRef.current = mr;
      setRecording(true);
    } catch (e) {
      toast.error("Microphone access denied");
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      mediaRecorderRef.current.stop();
    }
    setRecording(false);
  };

  const speakMessage = async (msg) => {
    if (playingId === msg.id) {
      audioRef.current?.pause();
      setPlayingId(null);
      return;
    }
    try {
      const r = await axios.post(`${API}/voice/tts`, { text: msg.text }, { responseType: "blob" });
      const url = URL.createObjectURL(r.data);
      if (audioRef.current) {
        audioRef.current.pause();
      }
      const audio = new Audio(url);
      audioRef.current = audio;
      audio.onended = () => { setPlayingId(null); URL.revokeObjectURL(url); };
      audio.onerror = () => { setPlayingId(null); URL.revokeObjectURL(url); };
      audio.play();
      setPlayingId(msg.id);
    } catch (e) {
      toast.error("Couldn't play audio");
    }
  };

  return (
    <div className="grid lg:grid-cols-4 gap-6 h-[calc(100vh-150px)]">
      <aside className="card-soft p-5 hidden lg:flex flex-col">
        <div className="flex items-center gap-2 mb-4">
          <BookOpen className="w-5 h-5 text-[#5BB9A6]" />
          <h3 className="font-[Outfit] text-lg font-semibold text-[#2F5D57]">Chat history</h3>
        </div>
        <button data-testid="new-chat-button" onClick={() => { setMessages([]); setSessionId(null); }}
                className="flex items-center gap-2 px-3 py-2 rounded-xl bg-[#5BB9A6] text-white text-sm font-medium hover:bg-[#4AA391] transition-colors">
          <MessageSquarePlus className="w-4 h-4" /> New chat
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
          AI provides educational information only. It does not diagnose or replace professional advice.
        </div>
      </aside>

      <main className="card-soft p-0 lg:col-span-3 flex flex-col overflow-hidden">
        <header className="px-6 py-4 border-b border-[#C2EBE1]/60 flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-[#5BB9A6] flex items-center justify-center">
            <Sparkles className="w-5 h-5 text-white" />
          </div>
          <div className="flex-1">
            <div className="font-[Outfit] font-semibold text-[#2F5D57]">MyHealthVoice AI</div>
            <div className="text-xs text-[#4B7A73]">Speaks your language · educational only</div>
          </div>
        </header>

        <div ref={scrollRef} className="flex-1 overflow-y-auto p-6 space-y-4">
          {messages.length === 0 && (
            <div className="text-center py-10">
              <div className="inline-flex w-16 h-16 rounded-2xl bg-[#A7E3D4]/40 items-center justify-center">
                <Sparkles className="w-7 h-7 text-[#5BB9A6]" />
              </div>
              <h3 className="mt-4 font-[Outfit] text-2xl font-bold text-[#2F5D57]">How can I help you today?</h3>
              <p className="text-sm text-[#4B7A73] mt-1">Type or tap the mic — I'll reply in the language you use.</p>
              <div className="mt-6 flex flex-wrap gap-2 justify-center">
                {SUGGESTIONS.map((s) => (
                  <button key={s} data-testid={`suggestion-${s.replace(/\s+/g, "-").toLowerCase()}`}
                          onClick={() => send(s)}
                          className="px-4 py-2 rounded-full bg-[#F7FFFD] border border-[#A7E3D4] text-sm text-[#2F5D57] hover:bg-[#D9F5EF] transition-colors">
                    {s}
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
                {m.role === "ai" && (
                  <button data-testid={`speak-${m.id}`} onClick={() => speakMessage(m)}
                          className="mt-2 inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-[#A7E3D4]/40 hover:bg-[#A7E3D4]/70 text-[#2F5D57] text-xs font-medium transition-colors">
                    {playingId === m.id ? <><Square className="w-3 h-3" /> Stop</> : <><Volume2 className="w-3 h-3" /> Listen</>}
                  </button>
                )}
                {m.sources && (
                  <div className="mt-3 pt-3 border-t border-[#C2EBE1]/50 flex flex-wrap gap-1.5">
                    {m.sources.map((s, i) => (
                      <span key={i} className="text-[10px] px-2 py-0.5 rounded-full bg-[#A7E3D4]/30 text-[#2F5D57]">
                        {s}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}

          {(thinking || transcribing) && (
            <div className="flex justify-start">
              <div className="bg-[#F7FFFD] border border-[#C2EBE1] rounded-2xl rounded-tl-sm p-4">
                {transcribing && <span className="text-xs text-[#4B7A73] mr-2">Transcribing…</span>}
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
              onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(input); } }}
              rows={1}
              placeholder={recording ? "Listening…" : "Ask anything about your health…"}
              className="flex-1 resize-none p-3 rounded-xl bg-[#F7FFFD] border border-[#C2EBE1] text-sm focus:outline-none focus:ring-2 focus:ring-[#5BB9A6]/40 max-h-32"
            />
            <button data-testid="send-message-button" onClick={() => send(input)} disabled={!input.trim() || thinking}
                    className="w-10 h-10 rounded-xl bg-[#5BB9A6] hover:bg-[#4AA391] flex items-center justify-center text-white transition-colors disabled:opacity-50">
              <Send className="w-4 h-4" />
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}
