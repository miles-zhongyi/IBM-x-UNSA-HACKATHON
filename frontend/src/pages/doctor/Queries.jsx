import { useEffect, useState } from "react";
import { api, fmtRelative } from "@/lib/api";
import { Paperclip, Sparkles, Send, Inbox } from "lucide-react";
import { toast } from "sonner";
import TranslateButton from "@/components/TranslateButton";
import { useUiI18n } from "@/lib/ui-i18n";

const FILTERS = [
  { id: "all", label: "All" },
  { id: "unanswered", label: "Unanswered" },
  { id: "answered", label: "Answered" },
  { id: "urgent", label: "Urgent" },
  { id: "archived", label: "Archived" },
];

export default function DoctorQueries() {
  const { t } = useUiI18n();
  const [filter, setFilter] = useState("all");
  const [threads, setThreads] = useState([]);
  const [selected, setSelected] = useState(null);
  const [thread, setThread] = useState(null);
  const [reply, setReply] = useState("");
  const [suggesting, setSuggesting] = useState(false);

  const loadThreads = (f = filter) => {
    const params = f !== "all" ? { status: f } : {};
    api.get("/queries", { params }).then((r) => {
      setThreads(r.data || []);
      if (!selected && r.data?.[0]) setSelected(r.data[0].id);
    });
  };

  useEffect(() => { loadThreads(filter); /* eslint-disable-next-line */ }, [filter]);

  useEffect(() => {
    if (!selected) return;
    api.get(`/queries/${selected}`).then((r) => setThread(r.data));
  }, [selected]);

  const sendReply = async () => {
    if (!reply.trim()) return;
    await api.post(`/queries/${selected}/messages`, { sender: "doctor", text: reply });
    setReply("");
    const r = await api.get(`/queries/${selected}`);
    setThread(r.data);
    loadThreads();
    toast.success(t("Reply sent"));
  };

  const aiSuggest = async () => {
    setSuggesting(true);
    try {
      const r = await api.post("/ai/suggest-reply", { thread_id: selected });
      setReply(r.data.suggestion);
    } finally { setSuggesting(false); }
  };

  return (
    <div className="space-y-4">
      <div>
        <h1 className="font-[Outfit] text-3xl md:text-4xl font-bold text-[#2F5D57]">{t("Patient Queries")}</h1>
        <p className="text-[#4B7A73] mt-1">{t("Reply to questions from your patients.")}</p>
      </div>

      <div className="grid lg:grid-cols-3 gap-4 h-[calc(100vh-220px)]">
        <div className="card-soft p-4 flex flex-col">
          <div className="flex flex-wrap gap-1.5 mb-3">
            {FILTERS.map((f) => (
              <button key={f.id} data-testid={`query-filter-${f.id}`} onClick={() => setFilter(f.id)}
                      className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-all ${
                        filter === f.id ? "bg-[#5BB9A6] text-white" : "bg-[#F7FFFD] text-[#4B7A73] hover:text-[#2F5D57]"
                      }`}>{t(f.label)}</button>
            ))}
          </div>
          <div className="overflow-y-auto flex-1 -mx-2 px-2 space-y-1">
            {threads.length === 0 && (
              <div className="text-center py-12 text-[#4B7A73]">
                <Inbox className="w-8 h-8 mx-auto mb-2 opacity-50" /> {t("No queries here.")}
              </div>
            )}
            {threads.map((item) => (
              <button key={item.id} onClick={() => setSelected(item.id)}
                      data-testid={`thread-${item.id}`}
                      className={`w-full text-left p-3 rounded-xl transition-colors ${
                        selected === item.id ? "bg-[#A7E3D4]/40" : "hover:bg-[#F7FFFD]"
                      }`}>
                <div className="flex items-center gap-2">
                  <div className="font-semibold text-sm text-[#2F5D57] flex-1 truncate">{item.patient_name}</div>
                  <span className="text-[10px] text-[#4B7A73]">{fmtRelative(item.last_message_at)}</span>
                </div>
                <div className="text-xs text-[#1A332F] truncate">{item.subject}</div>
                <div className="flex items-center gap-2 mt-1.5">
                  <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                    item.status === "urgent" ? "bg-[#E05A5A]/15 text-[#E05A5A]" :
                    item.status === "unanswered" ? "bg-[#E5A832]/15 text-[#A87D0E]" :
                    item.status === "answered" ? "bg-[#A7E3D4]/40 text-[#2F5D57]" : "bg-[#F7FFFD] text-[#4B7A73]"
                  }`}>{t(item.status)}</span>
                  {item.has_attachment && <Paperclip className="w-3 h-3 text-[#4B7A73]" />}
                </div>
              </button>
            ))}
          </div>
        </div>

        <div className="card-soft p-0 lg:col-span-2 flex flex-col overflow-hidden">
          {!thread ? (
            <div className="flex-1 flex items-center justify-center text-[#4B7A73]">{t("Select a conversation to view it")}</div>
          ) : (
            <>
              <div className="px-6 py-4 border-b border-[#C2EBE1]/60">
                <div className="font-[Outfit] font-semibold text-lg text-[#2F5D57]">{thread.thread.subject}</div>
                <div className="text-xs text-[#4B7A73]">with {thread.thread.patient_name}</div>
              </div>
              <div className="flex-1 overflow-y-auto p-6 space-y-4">
                {thread.messages.map((m) => (
                  <div key={m.id} className={`flex ${m.sender === "doctor" ? "justify-end" : "justify-start"}`}>
                    <div className={`max-w-[75%] p-4 rounded-2xl shadow-sm ${
                      m.sender === "doctor" ? "bg-[#5BB9A6] text-white rounded-tr-sm" : "bg-[#F7FFFD] border border-[#C2EBE1] text-[#1A332F] rounded-tl-sm"
                    }`}>
                      <div className="text-sm leading-relaxed">{m.text}</div>
                      <div className={`text-[10px] mt-1.5 ${m.sender === "doctor" ? "text-white/70" : "text-[#4B7A73]"}`}>
                        {m.sender_name} • {fmtRelative(m.created_at)}
                      </div>
                      <TranslateButton
                        text={m.text}
                        className={m.sender === "doctor" ? "bg-white/20 text-white hover:bg-white/30" : "bg-[#A7E3D4]/40 text-[#2F5D57] hover:bg-[#A7E3D4]/70"}
                      />
                    </div>
                  </div>
                ))}
              </div>
              <div className="border-t border-[#C2EBE1]/60 p-4 space-y-3">
                <textarea
                  data-testid="doctor-reply-input"
                  value={reply}
                  onChange={(e) => setReply(e.target.value)}
                  rows={3}
                  placeholder={t("Write your reply…")}
                  className="w-full p-3 rounded-xl bg-[#F7FFFD] border border-[#C2EBE1] text-sm focus:outline-none focus:ring-2 focus:ring-[#5BB9A6]/40"
                />
                <div className="flex items-center justify-between">
                  <button data-testid="ai-suggest-button" onClick={aiSuggest} disabled={suggesting}
                          className="inline-flex items-center gap-2 px-3 py-1.5 rounded-xl bg-[#A7E3D4]/40 hover:bg-[#A7E3D4]/70 text-[#2F5D57] text-xs font-medium transition-colors">
                    <Sparkles className="w-3.5 h-3.5" /> {suggesting ? t("Drafting…") : t("AI suggest reply")}
                  </button>
                  <button data-testid="send-reply-button" onClick={sendReply}
                          className="inline-flex items-center gap-2 px-5 py-2 rounded-xl bg-[#5BB9A6] text-white text-sm font-medium hover:bg-[#4AA391]">
                    <Send className="w-3.5 h-3.5" /> {t("Send")}
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
