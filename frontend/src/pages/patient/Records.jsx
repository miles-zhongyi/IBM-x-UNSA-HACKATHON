import { useEffect, useState } from "react";
import { api, fmtDate, fileUrl } from "@/lib/api";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { FileText, Download, Pill, AlertCircle, Stethoscope, Sparkles, Mail, Phone } from "lucide-react";

const TABS = [
  { id: "overview", label: "Overview" },
  { id: "documents", label: "Documents" },
  { id: "timeline", label: "Timeline" },
  { id: "ai", label: "AI Summaries" },
];

export default function PatientRecords() {
  const [data, setData] = useState(null);

  useEffect(() => {
    api.get("/patients").then(async (r) => {
      const me = r.data?.[0];
      if (!me) return;
      const detail = await api.get(`/patients/${me.id}`);
      setData(detail.data);
    });
  }, []);

  if (!data) return <div className="card-soft h-64 animate-pulse" />;
  const { patient, documents } = data;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-[Outfit] text-3xl md:text-4xl font-bold text-[#2F5D57]">My Health Records</h1>
        <p className="text-[#4B7A73] mt-1">Everything in one place.</p>
      </div>

      <Tabs defaultValue="overview">
        <TabsList className="bg-[#D9F5EF] p-1 rounded-xl">
          {TABS.map((t) => (
            <TabsTrigger key={t.id} value={t.id} data-testid={`records-tab-${t.id}`}
                         className="px-4 py-1.5 rounded-lg text-sm font-medium data-[state=active]:bg-[#5BB9A6] data-[state=active]:text-white text-[#4B7A73]">
              {t.label}
            </TabsTrigger>
          ))}
        </TabsList>

        <TabsContent value="overview" className="pt-6 grid lg:grid-cols-2 gap-6">
          <div className="card-soft p-6 flex items-start gap-4">
            <img src={patient.avatar} alt={patient.name} className="w-16 h-16 rounded-2xl object-cover ring-4 ring-[#A7E3D4]/40" />
            <div>
              <h3 className="font-[Outfit] text-xl font-semibold text-[#2F5D57]">{patient.name}</h3>
              <p className="text-sm text-[#4B7A73]">{patient.age} • {patient.sex}</p>
              <div className="mt-3 space-y-1.5 text-sm text-[#1A332F]">
                <div className="flex items-center gap-2"><Mail className="w-4 h-4 text-[#5BB9A6]" /> {patient.email}</div>
                <div className="flex items-center gap-2"><Phone className="w-4 h-4 text-[#5BB9A6]" /> {patient.phone}</div>
              </div>
            </div>
          </div>
          <div className="card-soft p-6">
            <div className="grid grid-cols-3 gap-3">
              <div className="p-3 rounded-xl bg-[#F7FFFD]">
                <Pill className="w-4 h-4 text-[#5BB9A6] mb-1.5" />
                <div className="text-xs text-[#4B7A73] uppercase tracking-wider">Meds</div>
                <div className="text-sm font-semibold text-[#2F5D57]">{patient.medications.length}</div>
              </div>
              <div className="p-3 rounded-xl bg-[#F7FFFD]">
                <AlertCircle className="w-4 h-4 text-[#E5A832] mb-1.5" />
                <div className="text-xs text-[#4B7A73] uppercase tracking-wider">Allergies</div>
                <div className="text-sm font-semibold text-[#2F5D57]">{patient.allergies.length}</div>
              </div>
              <div className="p-3 rounded-xl bg-[#F7FFFD]">
                <Stethoscope className="w-4 h-4 text-[#2F5D57] mb-1.5" />
                <div className="text-xs text-[#4B7A73] uppercase tracking-wider">Conditions</div>
                <div className="text-sm font-semibold text-[#2F5D57]">{patient.conditions.length}</div>
              </div>
            </div>
            <div className="mt-4 space-y-3">
              <div>
                <div className="text-xs uppercase tracking-wider text-[#4B7A73]">Medications</div>
                <div className="text-sm text-[#1A332F]">{patient.medications.join(", ") || "None"}</div>
              </div>
              <div>
                <div className="text-xs uppercase tracking-wider text-[#4B7A73]">Allergies</div>
                <div className="text-sm text-[#1A332F]">{patient.allergies.join(", ") || "None"}</div>
              </div>
              <div>
                <div className="text-xs uppercase tracking-wider text-[#4B7A73]">Conditions</div>
                <div className="text-sm text-[#1A332F]">{patient.conditions.join(", ") || "None"}</div>
              </div>
            </div>
          </div>
        </TabsContent>

        <TabsContent value="documents" className="pt-6">
          <div className="grid sm:grid-cols-2 gap-4">
            {documents.length === 0 && (
              <div className="col-span-2 card-soft p-10 text-center text-[#4B7A73]">No documents yet. Your doctor will upload reports here.</div>
            )}
            {documents.map((d) => (
              <div key={d.id} className="card-soft p-5 flex items-start gap-4">
                <div className="w-12 h-12 rounded-xl bg-[#A7E3D4]/40 flex items-center justify-center">
                  <FileText className="w-5 h-5 text-[#2F5D57]" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="font-semibold text-[#2F5D57] truncate">{d.title}</div>
                  <div className="text-xs text-[#4B7A73]">{d.doc_type} • {fmtDate(d.created_at)}</div>
                </div>
                {d.status === "completed" && (
                  <a href={fileUrl(d.storage_path)} target="_blank" rel="noopener noreferrer"
                     className="w-10 h-10 rounded-xl bg-[#5BB9A6] hover:bg-[#4AA391] flex items-center justify-center transition-colors">
                    <Download className="w-4 h-4 text-white" />
                  </a>
                )}
              </div>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="timeline" className="pt-6">
          <div className="card-soft p-6">
            <ol className="border-l-2 border-[#A7E3D4] pl-6 space-y-6">
              {documents.length === 0 && <li className="text-sm text-[#4B7A73]">Your timeline will appear here.</li>}
              {documents.map((d) => (
                <li key={d.id} className="relative">
                  <span className="absolute -left-[33px] top-1 w-3.5 h-3.5 rounded-full bg-[#5BB9A6] ring-4 ring-[#D9F5EF]" />
                  <div className="text-sm font-semibold text-[#2F5D57]">{d.title}</div>
                  <div className="text-xs text-[#4B7A73]">{fmtDate(d.created_at)} • {d.doc_type}</div>
                </li>
              ))}
            </ol>
          </div>
        </TabsContent>

        <TabsContent value="ai" className="pt-6">
          <div className="card-soft p-6">
            <div className="flex items-center gap-2 mb-3">
              <Sparkles className="w-5 h-5 text-[#5BB9A6]" />
              <h3 className="font-[Outfit] text-lg font-semibold text-[#2F5D57]">In simple terms</h3>
            </div>
            <p className="text-base text-[#1A332F] leading-relaxed">{patient.ai_summary}</p>
            <p className="mt-3 text-xs text-[#4B7A73] italic">Educational only. Always confirm changes with your doctor.</p>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
