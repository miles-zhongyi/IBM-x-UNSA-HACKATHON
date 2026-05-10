import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { api, fmtDate, fileUrl } from "@/lib/api";
import { ArrowLeft, FileText, Download, Pill, AlertCircle, Stethoscope, Mail, Phone, Sparkles, Calendar, Trash2 } from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useUiI18n } from "@/lib/ui-i18n";

const TABS = [
  { id: "overview", label: "Overview" },
  { id: "history", label: "Medical History" },
  { id: "documents", label: "Documents & Scans" },
  { id: "conversations", label: "Conversations" },
  { id: "ai", label: "AI Summary" },
];

const InfoChip = ({ icon: Icon, label, value, t }) => (
  <div className="flex items-start gap-3 p-3 rounded-xl bg-[#F7FFFD]">
    <Icon className="w-4 h-4 text-[#5BB9A6] mt-0.5" />
    <div>
      <div className="text-xs uppercase tracking-wider text-[#4B7A73]">{t(label)}</div>
      <div className="text-sm font-semibold text-[#2F5D57]">{value || "—"}</div>
    </div>
  </div>
);

export default function PatientProfile() {
  const { t } = useUiI18n();
  const { id } = useParams();
  const [data, setData] = useState(null);

  useEffect(() => {
    api.get(`/patients/${id}`).then((r) => setData(r.data));
  }, [id]);

  const deleteDocument = async (documentId) => {
    if (!confirm("Are you sure you want to delete this document?")) return;
    try {
      await api.delete(`/patients/${id}/documents/${documentId}`);
      // Refresh the data
      const response = await api.get(`/patients/${id}`);
      setData(response.data);
    } catch (error) {
      alert("Failed to delete document");
    }
  };

  if (!data) return <div className="card-soft h-64 animate-pulse" />;

  const { patient, documents, threads } = data;

  return (
    <div className="space-y-6">
      <Link to="/doctor/patients" className="inline-flex items-center gap-2 text-sm text-[#4B7A73] hover:text-[#2F5D57]">
        <ArrowLeft className="w-4 h-4" /> {t("Back to patients")}
      </Link>

      <div className="card-soft p-6 flex items-center gap-6 flex-wrap">
        <img src={patient.avatar} alt={patient.name} className="w-20 h-20 rounded-2xl object-cover ring-4 ring-[#A7E3D4]/40" />
        <div className="flex-1 min-w-[200px]">
          <h1 className="font-[Outfit] text-3xl font-bold text-[#2F5D57]">{patient.name}</h1>
          <div className="text-sm text-[#4B7A73] mt-1">{patient.age} {t("years")} • {patient.sex} • {t(patient.status)}</div>
          <div className="flex flex-wrap gap-2 mt-3">
            {patient.conditions.map((c) => (
              <span key={c} className="px-2.5 py-0.5 rounded-full text-xs bg-[#A7E3D4]/40 text-[#2F5D57] font-medium">{c}</span>
            ))}
          </div>
        </div>
        <div className="text-right">
          <div className="text-xs uppercase tracking-wider text-[#4B7A73]">{t("Pending questions")}</div>
          <div className="font-[Outfit] text-3xl font-bold text-[#2F5D57]">{patient.pending_questions}</div>
        </div>
      </div>

      <Tabs defaultValue="overview" className="w-full">
        <TabsList className="bg-[#D9F5EF] p-1 rounded-xl">
          {TABS.map((tab) => (
            <TabsTrigger
              key={tab.id}
              value={tab.id}
              data-testid={`tab-${tab.id}`}
              className="px-4 py-1.5 rounded-lg text-sm font-medium data-[state=active]:bg-[#5BB9A6] data-[state=active]:text-white text-[#4B7A73]"
            >
              {t(tab.label)}
            </TabsTrigger>
          ))}
        </TabsList>

        <TabsContent value="overview" className="pt-6">
          <div className="grid lg:grid-cols-2 gap-6">
            <div className="card-soft p-6">
              <h3 className="font-[Outfit] text-lg font-semibold text-[#2F5D57] mb-4">{t("Contact")}</h3>
              <div className="space-y-3">
                <InfoChip icon={Mail} label="Email" value={patient.email} t={t} />
                <InfoChip icon={Phone} label="Phone" value={patient.phone} t={t} />
              </div>
            </div>
            <div className="card-soft p-6">
              <h3 className="font-[Outfit] text-lg font-semibold text-[#2F5D57] mb-4">{t("Quick facts")}</h3>
              <div className="grid grid-cols-2 gap-3">
                <InfoChip icon={Pill} label="Medications" value={patient.medications.join(", ")} t={t} />
                <InfoChip icon={AlertCircle} label="Allergies" value={patient.allergies.join(", ")} t={t} />
                <InfoChip icon={Stethoscope} label="Conditions" value={patient.conditions.join(", ")} t={t} />
                <InfoChip icon={Calendar} label="Last activity" value={fmtDate(patient.last_activity)} t={t} />
              </div>
            </div>
          </div>
        </TabsContent>

        <TabsContent value="history" className="pt-6">
          <div className="card-soft p-6">
            <h3 className="font-[Outfit] text-lg font-semibold text-[#2F5D57] mb-4">{t("Timeline")}</h3>
            <ol className="border-l-2 border-[#A7E3D4] pl-6 space-y-6">
              {[...documents].slice(0, 6).map((d) => (
                <li key={d.id} className="relative">
                  <span className="absolute -left-[33px] top-1 w-3.5 h-3.5 rounded-full bg-[#5BB9A6] ring-4 ring-[#D9F5EF]" />
                  <div className="text-sm font-semibold text-[#2F5D57]">{d.title}</div>
                  <div className="text-xs text-[#4B7A73]">{fmtDate(d.created_at)} • {d.doc_type}</div>
                </li>
              ))}
              {documents.length === 0 && <li className="text-sm text-[#4B7A73]">{t("No history yet.")}</li>}
            </ol>
          </div>
        </TabsContent>

        <TabsContent value="documents" className="pt-6">
          <div className="grid md:grid-cols-2 gap-4">
            {documents.length === 0 && <div className="card-soft p-8 text-center text-[#4B7A73]">{t("No documents uploaded yet.")}</div>}
            {documents.map((d) => (
              <div key={d.id} className="card-soft p-5 flex items-start gap-4">
                <div className="w-12 h-12 rounded-xl bg-[#A7E3D4]/40 flex items-center justify-center">
                  <FileText className="w-5 h-5 text-[#2F5D57]" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="font-semibold text-[#2F5D57] truncate">{d.title}</div>
                  <div className="text-xs text-[#4B7A73]">{d.doc_type} • {fmtDate(d.created_at)}</div>
                  <span className={`inline-block mt-2 px-2 py-0.5 rounded-full text-xs ${
                    d.status === "completed" ? "bg-[#A7E3D4]/40 text-[#2F5D57]" : "bg-[#E05A5A]/15 text-[#E05A5A]"
                  }`}>{d.status}</span>
                </div>
                <div className="flex flex-col gap-2">
                  {d.status === "completed" && (
                    <a href={fileUrl(d.storage_path)} target="_blank" rel="noopener noreferrer"
                       className="w-10 h-10 rounded-xl bg-[#5BB9A6] hover:bg-[#4AA391] flex items-center justify-center transition-colors">
                      <Download className="w-4 h-4 text-white" />
                    </a>
                  )}
                  <button
                    onClick={() => deleteDocument(d.id)}
                    className="w-10 h-10 rounded-xl bg-[#E05A5A] hover:bg-[#C44A4A] flex items-center justify-center transition-colors"
                    title="Delete document"
                  >
                    <Trash2 className="w-4 h-4 text-white" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="conversations" className="pt-6">
          <div className="card-soft p-6">
            {threads.length === 0 ? (
            <p className="text-sm text-[#4B7A73] text-center py-8">{t("No conversations yet.")}</p>
            ) : (
              <ul className="divide-y divide-[#C2EBE1]/60">
                {threads.map((item) => (
                  <li key={item.id} className="py-3 flex items-center gap-4">
                    <div className={`w-2 h-2 rounded-full ${item.status === "urgent" ? "bg-[#E05A5A]" : item.status === "unanswered" ? "bg-[#E5A832]" : "bg-[#5BB9A6]"}`} />
                    <div className="flex-1">
                      <div className="font-semibold text-[#2F5D57]">{item.subject}</div>
                      <div className="text-xs text-[#4B7A73]">{fmtDate(item.last_message_at)}</div>
                    </div>
                    <span className="text-xs text-[#4B7A73] capitalize">{t(item.status)}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </TabsContent>

        <TabsContent value="ai" className="pt-6">
          <div className="card-soft p-6">
            <div className="flex items-center gap-2 mb-3">
              <Sparkles className="w-5 h-5 text-[#5BB9A6]" />
              <h3 className="font-[Outfit] text-lg font-semibold text-[#2F5D57]">{t("AI Health Summary")}</h3>
            </div>
            <p className="text-base text-[#1A332F] leading-relaxed">{patient.ai_summary || t("No AI summary yet.")}</p>
            <div className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-3">
              <InfoChip icon={Pill} label="Medications" value={patient.medications.join(", ") || t("None")} t={t} />
              <InfoChip icon={Stethoscope} label="Conditions" value={patient.conditions.join(", ") || t("None")} t={t} />
              <InfoChip icon={AlertCircle} label="Allergies" value={patient.allergies.join(", ") || t("None")} t={t} />
            </div>
            <p className="mt-4 text-xs text-[#4B7A73] italic">{t("AI summaries are educational and informational only — not a substitute for clinical judgment.")}</p>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
