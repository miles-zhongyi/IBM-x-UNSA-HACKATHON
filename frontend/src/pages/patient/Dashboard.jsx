import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, fmtRelative } from "@/lib/api";
import { Sparkles, MessageSquare, FileText, UploadCloud, Pill, AlertCircle, HeartPulse, Calendar } from "lucide-react";
import { useUiI18n } from "@/lib/ui-i18n";

export default function PatientDashboard() {
  const { t } = useUiI18n();
  const [data, setData] = useState(null);

  useEffect(() => {
    api.get("/patients").then(async (r) => {
      const me = r.data?.[0];
      if (!me) return;
      const dash = await api.get(`/dashboard/patient/${me.id}`);
      setData(dash.data);
    });
  }, []);

  if (!data) return <div className="card-soft h-64 animate-pulse" />;
  const { patient, recent_documents, recent_threads } = data;

  return (
    <div className="space-y-8">
      <div className="card-soft p-8 relative overflow-hidden">
        <div className="absolute -right-10 -top-10 w-56 h-56 rounded-full bg-[#A7E3D4]/40 blur-3xl pointer-events-none" />
        <div className="relative">
          <span className="inline-flex px-3 py-1 rounded-full bg-[#A7E3D4]/40 text-[#2F5D57] text-xs font-semibold uppercase tracking-wider">{t("Welcome back")}</span>
          <h1 className="mt-3 font-[Outfit] text-3xl md:text-4xl font-bold text-[#2F5D57]">{t("Hello")}, {patient.name.split(" ")[0]}</h1>
          <p className="text-[#4B7A73] mt-2 max-w-xl">{t("Here's your health at a glance. Take a deep breath — you're doing great.")}</p>
        </div>
      </div>

      <div className="grid lg:grid-cols-12 gap-6">
        <div className="lg:col-span-8 card-soft p-6">
          <div className="flex items-center gap-2 mb-4">
            <HeartPulse className="w-5 h-5 text-[#5BB9A6]" />
            <h3 className="font-[Outfit] text-xl font-semibold text-[#2F5D57]">{t("Health summary")}</h3>
          </div>
          <div className="grid sm:grid-cols-3 gap-4">
            <div className="p-4 rounded-xl bg-[#F7FFFD]">
              <Pill className="w-4 h-4 text-[#5BB9A6] mb-2" />
              <div className="text-xs uppercase tracking-wider text-[#4B7A73]">{t("Medications")}</div>
              <div className="mt-1 text-sm font-semibold text-[#2F5D57]">{patient.medications.join(", ") || t("None")}</div>
            </div>
            <div className="p-4 rounded-xl bg-[#F7FFFD]">
              <AlertCircle className="w-4 h-4 text-[#E5A832] mb-2" />
              <div className="text-xs uppercase tracking-wider text-[#4B7A73]">{t("Allergies")}</div>
              <div className="mt-1 text-sm font-semibold text-[#2F5D57]">{patient.allergies.join(", ") || t("None")}</div>
            </div>
            <div className="p-4 rounded-xl bg-[#F7FFFD]">
              <HeartPulse className="w-4 h-4 text-[#2F5D57] mb-2" />
              <div className="text-xs uppercase tracking-wider text-[#4B7A73]">{t("Conditions")}</div>
              <div className="mt-1 text-sm font-semibold text-[#2F5D57]">{patient.conditions.join(", ") || t("None")}</div>
            </div>
          </div>
          <div className="mt-6 p-4 rounded-xl bg-[#A7E3D4]/30">
            <div className="flex items-center gap-2 text-xs uppercase tracking-wider text-[#4B7A73] font-semibold">
              <Sparkles className="w-3.5 h-3.5" /> {t("Latest AI summary")}
            </div>
            <p className="mt-2 text-sm text-[#1A332F] leading-relaxed">{patient.ai_summary}</p>
          </div>
        </div>

        <div className="lg:col-span-4 space-y-4">
          <div className="card-soft p-6">
            <div className="flex items-center gap-2 mb-3">
              <Calendar className="w-5 h-5 text-[#5BB9A6]" />
              <h3 className="font-[Outfit] text-lg font-semibold text-[#2F5D57]">{t("Upcoming")}</h3>
            </div>
            <div className="space-y-3">
              <div className="p-3 rounded-xl bg-[#F7FFFD]">
                <div className="text-xs text-[#4B7A73]">Tue, Mar 11 · 10:30 AM</div>
                <div className="text-sm font-semibold text-[#2F5D57]">{t("Follow-up with Dr. Chen")}</div>
              </div>
              <div className="p-3 rounded-xl bg-[#F7FFFD]">
                <div className="text-xs text-[#4B7A73]">Fri, Mar 21</div>
                <div className="text-sm font-semibold text-[#2F5D57]">{t("Quarterly lab work")}</div>
              </div>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Link to="/patient/ai-assistant" data-testid="quick-ask-ai" className="card-soft p-4 text-center group">
              <Sparkles className="w-5 h-5 mx-auto text-[#5BB9A6] group-hover:scale-110 transition-transform" />
              <div className="mt-2 text-sm font-semibold text-[#2F5D57]">{t("Ask AI")}</div>
            </Link>
            <Link to="/patient/ask-doctor" data-testid="quick-ask-doctor" className="card-soft p-4 text-center group">
              <MessageSquare className="w-5 h-5 mx-auto text-[#5BB9A6] group-hover:scale-110 transition-transform" />
              <div className="mt-2 text-sm font-semibold text-[#2F5D57]">{t("Ask Doctor")}</div>
            </Link>
            <Link to="/patient/records" data-testid="quick-records" className="card-soft p-4 text-center group">
              <FileText className="w-5 h-5 mx-auto text-[#5BB9A6] group-hover:scale-110 transition-transform" />
              <div className="mt-2 text-sm font-semibold text-[#2F5D57]">{t("Documents")}</div>
            </Link>
            <Link to="/patient/records#upload" data-testid="quick-upload" className="card-soft p-4 text-center group">
              <UploadCloud className="w-5 h-5 mx-auto text-[#5BB9A6] group-hover:scale-110 transition-transform" />
              <div className="mt-2 text-sm font-semibold text-[#2F5D57]">{t("Upload")}</div>
            </Link>
          </div>
        </div>
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        <div className="card-soft p-6">
          <h3 className="font-[Outfit] text-lg font-semibold text-[#2F5D57] mb-4">{t("Recent updates")}</h3>
          {recent_threads.length === 0 ? (
            <p className="text-sm text-[#4B7A73]">{t("Nothing new yet.")}</p>
          ) : (
            <ul className="space-y-3">
              {recent_threads.slice(0, 4).map((t) => (
                <li key={t.id} className="flex items-start gap-3 p-3 rounded-xl hover:bg-[#F7FFFD] transition-colors">
                  <div className="w-9 h-9 rounded-xl bg-[#A7E3D4]/40 flex items-center justify-center">
                    <MessageSquare className="w-4 h-4 text-[#2F5D57]" />
                  </div>
                  <div className="flex-1">
                    <div className="text-sm font-semibold text-[#2F5D57]">{t.subject}</div>
                    <div className="text-xs text-[#4B7A73]">{fmtRelative(t.last_message_at)} • {t.status}</div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
        <div className="card-soft p-6">
          <h3 className="font-[Outfit] text-lg font-semibold text-[#2F5D57] mb-4">{t("Recent documents")}</h3>
          {recent_documents.length === 0 ? (
            <p className="text-sm text-[#4B7A73]">{t("No documents yet.")}</p>
          ) : (
            <ul className="space-y-3">
              {recent_documents.slice(0, 4).map((d) => (
                <li key={d.id} className="flex items-start gap-3 p-3 rounded-xl hover:bg-[#F7FFFD] transition-colors">
                  <div className="w-9 h-9 rounded-xl bg-[#A7E3D4]/40 flex items-center justify-center">
                    <FileText className="w-4 h-4 text-[#2F5D57]" />
                  </div>
                  <div className="flex-1">
                    <div className="text-sm font-semibold text-[#2F5D57]">{d.title}</div>
                    <div className="text-xs text-[#4B7A73]">{d.doc_type} • {fmtRelative(d.created_at)}</div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
