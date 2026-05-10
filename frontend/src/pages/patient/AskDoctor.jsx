import { useEffect, useState } from "react";
import { api, fmtRelative } from "@/lib/api";
import { Plus, Send, Paperclip, Inbox } from "lucide-react";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { toast } from "sonner";
import TranslateButton from "@/components/TranslateButton";

const FILTERS = [
  { id: "all", label: "All" },
  { id: "unanswered", label: "Awaiting reply" },
  { id: "answered", label: "Answered" },
];

export default function AskDoctor() {
  const [me, setMe] = useState(null);
  const [filter, setFilter] = useState("all");
  const [threads, setThreads] = useState([]);
  const [selected, setSelected] = useState(null);
  const [thread, setThread] = useState(null);
  const [reply, setReply] = useState("");
  const [open, setOpen] = useState(false);
  const [subject, setSubject] = useState("");
  const [text, setText] = useState("");

  useEffect(() => { api.get("/patients").then((r) => setMe(r.data?.[0])); }, []);

  const load = async () => {
    if (!me) return;
    const params = { patient_id: me.id };
    if (filter !== "all") params.status = filter;
    const r = await api.get("/queries", { params });
    setThreads(r.data || []);
    if (!selected && r.data?.[0]) setSelected(r.data[0].id);
  };

  useEffect(() => { if (me) load(); /* eslint-disable-next-line */ }, [me, filter]);

  useEffect(() => {
    if (!selected) return;
    api.get(`/queries/${selected}`).then((r) => setThread(r.data));
  }, [selected]);

  const send = async () => {
    if (!reply.trim()) return;
    await api.post(`/queries/${selected}/messages`, { sender: "patient", text: reply });
    setReply("");
    const r = await api.get(`/queries/${selected}`);
    setThread(r.data);
    load();
  };

  const newQuestion = async () => {
    if (!subject.trim() || !text.trim()) return;
    const r = await api.post("/queries", { patient_id: me.id, subject, text });
    setSubject(""); setText(""); setOpen(false);
    setSelected(r.data.id);
    load();
    toast.success("Your question was sent to your doctor");
  };

  return (
    <div className="space-y-4">
      <div className="flex items-end justify-between flex-wrap gap-3">
        <div>
          <h1 className="font-[Outfit] text-3xl md:text-4xl font-bold text-[#2F5D57]">Ask Your Doctor</h1>
          <p className="text-[#4B7A73] mt-1">A direct, private line to your care team.</p>
        </div>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <button data-testid="new-question-button" className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-[#5BB9A6] text-white font-medium hover:bg-[#4AA391]">
              <Plus className="w-4 h-4" /> New question
            </button>
          </DialogTrigger>
          <DialogContent className="bg-[#F7FFFD] border-[#C2EBE1]">
            <DialogHeader>
              <DialogTitle className="font-[Outfit] text-[#2F5D57]">New question</DialogTitle>
            </DialogHeader>
            <div className="space-y-3">
              <input data-testid="new-question-subject" value={subject} onChange={(e) => setSubject(e.target.value)}
                     placeholder="Subject" className="w-full px-3 py-2 rounded-xl border border-[#C2EBE1] bg-[#F7FFFD] text-sm focus:outline-none focus:ring-2 focus:ring-[#5BB9A6]/40" />
              <textarea data-testid="new-question-text" value={text} onChange={(e) => setText(e.target.value)} rows={5}
                        placeholder="Describe what's on your mind…" className="w-full px-3 py-2 rounded-xl border border-[#C2EBE1] bg-[#F7FFFD] text-sm focus:outline-none focus:ring-2 focus:ring-[#5BB9A6]/40" />
            </div>
            <DialogFooter>
              <button data-testid="submit-question" onClick={newQuestion} className="px-5 py-2 rounded-xl bg-[#5BB9A6] text-white font-medium hover:bg-[#4AA391]">Send</button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      <div className="grid lg:grid-cols-3 gap-4 h-[calc(100vh-220px)]">
        <div className="card-soft p-4 flex flex-col">
          <div className="flex gap-1.5 mb-3">
            {FILTERS.map((f) => (
              <button key={f.id} onClick={() => setFilter(f.id)}
                      data-testid={`ask-filter-${f.id}`}
                      className={`px-3 py-1 rounded-lg text-xs font-medium transition-all ${
                        filter === f.id ? "bg-[#5BB9A6] text-white" : "bg-[#F7FFFD] text-[#4B7A73] hover:text-[#2F5D57]"
                      }`}>{f.label}</button>
            ))}
          </div>
          <div className="overflow-y-auto flex-1 -mx-2 px-2 space-y-1">
            {threads.length === 0 && (
              <div className="text-center py-12 text-[#4B7A73]">
                <Inbox className="w-8 h-8 mx-auto mb-2 opacity-50" /> No messages yet.
              </div>
            )}
            {threads.map((t) => (
              <button key={t.id} onClick={() => setSelected(t.id)}
                      data-testid={`patient-thread-${t.id}`}
                      className={`w-full text-left p-3 rounded-xl transition-colors ${
                        selected === t.id ? "bg-[#A7E3D4]/40" : "hover:bg-[#F7FFFD]"
                      }`}>
                <div className="font-semibold text-sm text-[#2F5D57] truncate">{t.subject}</div>
                <div className="flex items-center justify-between mt-1.5">
                  <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                    t.status === "answered" ? "bg-[#A7E3D4]/40 text-[#2F5D57]" :
                    t.status === "urgent" ? "bg-[#E05A5A]/15 text-[#E05A5A]" :
                    "bg-[#E5A832]/15 text-[#A87D0E]"
                  }`}>{t.status === "unanswered" ? "Awaiting reply" : t.status}</span>
                  <span className="text-[10px] text-[#4B7A73]">{fmtRelative(t.last_message_at)}</span>
                </div>
              </button>
            ))}
          </div>
        </div>

        <div className="card-soft p-0 lg:col-span-2 flex flex-col overflow-hidden">
          {!thread ? (
            <div className="flex-1 flex items-center justify-center text-[#4B7A73]">Select a conversation.</div>
          ) : (
            <>
              <div className="px-6 py-4 border-b border-[#C2EBE1]/60">
                <div className="font-[Outfit] font-semibold text-lg text-[#2F5D57]">{thread.thread.subject}</div>
                <div className="text-xs text-[#4B7A73]">with Dr. Sarah Chen</div>
              </div>
              <div className="flex-1 overflow-y-auto p-6 space-y-4">
                {thread.messages.map((m) => (
                  <div key={m.id} className={`flex ${m.sender === "patient" ? "justify-end" : "justify-start"}`}>
                    <div className={`max-w-[78%] p-4 shadow-sm ${
                      m.sender === "patient"
                        ? "bg-[#5BB9A6] text-white rounded-2xl rounded-tr-sm"
                        : "bg-[#F7FFFD] border border-[#C2EBE1] text-[#1A332F] rounded-2xl rounded-tl-sm"
                    }`}>
                      <div className="text-sm leading-relaxed">{m.text}</div>
                      <div className={`text-[10px] mt-1.5 ${m.sender === "patient" ? "text-white/70" : "text-[#4B7A73]"}`}>
                        {m.sender_name} • {fmtRelative(m.created_at)}
                      </div>
                      <TranslateButton
                        text={m.text}
                        className={m.sender === "patient" ? "bg-white/20 text-white hover:bg-white/30" : "bg-[#A7E3D4]/40 text-[#2F5D57] hover:bg-[#A7E3D4]/70"}
                      />
                    </div>
                  </div>
                ))}
              </div>
              <div className="border-t border-[#C2EBE1]/60 p-4 flex items-end gap-2">
                <button className="w-10 h-10 rounded-xl bg-[#F7FFFD] hover:bg-[#A7E3D4]/40 flex items-center justify-center text-[#4B7A73]">
                  <Paperclip className="w-4 h-4" />
                </button>
                <textarea
                  data-testid="patient-reply-input"
                  value={reply}
                  onChange={(e) => setReply(e.target.value)}
                  rows={1}
                  placeholder="Write a follow-up…"
                  className="flex-1 resize-none p-3 rounded-xl bg-[#F7FFFD] border border-[#C2EBE1] text-sm focus:outline-none focus:ring-2 focus:ring-[#5BB9A6]/40 max-h-32"
                />
                <button data-testid="patient-send-button" onClick={send}
                        className="w-10 h-10 rounded-xl bg-[#5BB9A6] hover:bg-[#4AA391] flex items-center justify-center text-white">
                  <Send className="w-4 h-4" />
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
