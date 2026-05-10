import { useEffect, useState, useRef } from "react";
import { useLocation } from "react-router-dom";
import { api, fmtDate, fileUrl } from "@/lib/api";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { FileText, Download, Pill, AlertCircle, Stethoscope, Sparkles, Mail, Phone, Trash2, Upload, Check, Loader2, X, RotateCw } from "lucide-react";
import { toast } from "sonner";
import { useUiI18n } from "@/lib/ui-i18n";

const TABS = [
  { id: "overview", label: "Overview" },
  { id: "documents", label: "Documents" },
  { id: "upload", label: "Upload" },
  { id: "timeline", label: "Timeline" },
  { id: "ai", label: "AI Summaries" },
];

const DOC_TYPES = [
  { id: "report", label: "Lab Report" },
  { id: "scan", label: "Imaging / Scan" },
  { id: "prescription", label: "Prescription" },
  { id: "other", label: "Other" },
];

export default function PatientRecords() {
  const { t } = useUiI18n();
  const location = useLocation();
  const [data, setData] = useState(null);
  const [deletingId, setDeletingId] = useState(null);
  const [activeTab, setActiveTab] = useState("overview");
  const [uploadStep, setUploadStep] = useState(1);
  const [docType, setDocType] = useState("");
  const [file, setFile] = useState(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadStatus, setUploadStatus] = useState(null); // null | uploading | processing | completed | failed
  const fileInputRef = useRef(null);

  useEffect(() => {
    api.get("/patients").then(async (r) => {
      const me = r.data?.[0];
      if (!me) return;
      const detail = await api.get(`/patients/${me.id}`);
      setData(detail.data);
    });
  }, []);

  useEffect(() => {
    const hash = location.hash.replace('#', '');
    if (TABS.some(tab => tab.id === hash)) {
      setActiveTab(hash);
    }
  }, [location.hash]);

  if (!data) return <div className="card-soft h-64 animate-pulse" />;
  const { patient, documents } = data;

  const deleteDocument = async (docId, title) => {
    const ok = window.confirm(`${t("Delete")} "${title || t("this document")}"? ${t("This cannot be undone.")}`);
    if (!ok) return;
    setDeletingId(docId);
    try {
      await api.delete(`/patients/${patient.id}/documents/${docId}`);
      setData((prev) => ({
        ...prev,
        documents: (prev?.documents || []).filter((d) => d.id !== docId),
      }));
      toast.success(t("Document deleted."));
    } catch {
      toast.error(t("Could not delete document. Please try again."));
    } finally {
      setDeletingId(null);
    }
  };

  const resetUpload = () => {
    setUploadStep(1);
    setDocType("");
    setFile(null);
    setUploadProgress(0);
    setUploadStatus(null);
  };

  const onDrop = (e) => {
    e.preventDefault();
    const f = e.dataTransfer.files?.[0];
    if (f) setFile(f);
  };

  const handleUpload = async () => {
    if (!file || !patient) return;
    setUploadStatus("uploading");
    setUploadProgress(0);
    const fd = new FormData();
    fd.append("patient_id", patient.id);
    fd.append("doc_type", docType);
    fd.append("title", file.name);
    fd.append("file", file);
    try {
      await api.post("/upload", fd, {
        headers: { "Content-Type": "multipart/form-data" },
        onUploadProgress: (e) => setUploadProgress(Math.round((e.loaded / (e.total || 1)) * 100)),
      });
      setUploadStatus("processing");
      setTimeout(() => {
        setUploadStatus("completed");
        toast.success("Document uploaded and processed");
        // Refresh documents
        api.get(`/patients/${patient.id}`).then((r) => setData(r.data));
      }, 800);
    } catch (e) {
      console.error(e);
      setUploadStatus("failed");
      toast.error("Upload failed");
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-[Outfit] text-3xl md:text-4xl font-bold text-[#2F5D57]">{t("My Health Records")}</h1>
        <p className="text-[#4B7A73] mt-1">{t("Everything in one place.")}</p>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="bg-[#D9F5EF] p-1 rounded-xl">
          {TABS.map((tab) => (
            <TabsTrigger key={tab.id} value={tab.id} data-testid={`records-tab-${tab.id}`}
                         className="px-4 py-1.5 rounded-lg text-sm font-medium data-[state=active]:bg-[#5BB9A6] data-[state=active]:text-white text-[#4B7A73]">
              {t(tab.label)}
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
                <div className="text-xs text-[#4B7A73] uppercase tracking-wider">{t("Meds")}</div>
                <div className="text-sm font-semibold text-[#2F5D57]">{patient.medications.length}</div>
              </div>
              <div className="p-3 rounded-xl bg-[#F7FFFD]">
                <AlertCircle className="w-4 h-4 text-[#E5A832] mb-1.5" />
                <div className="text-xs text-[#4B7A73] uppercase tracking-wider">{t("Allergies")}</div>
                <div className="text-sm font-semibold text-[#2F5D57]">{patient.allergies.length}</div>
              </div>
              <div className="p-3 rounded-xl bg-[#F7FFFD]">
                <Stethoscope className="w-4 h-4 text-[#2F5D57] mb-1.5" />
                <div className="text-xs text-[#4B7A73] uppercase tracking-wider">{t("Conditions")}</div>
                <div className="text-sm font-semibold text-[#2F5D57]">{patient.conditions.length}</div>
              </div>
            </div>
            <div className="mt-4 space-y-3">
              <div>
                <div className="text-xs uppercase tracking-wider text-[#4B7A73]">{t("Medications")}</div>
                <div className="text-sm text-[#1A332F]">{patient.medications.join(", ") || t("None")}</div>
              </div>
              <div>
                <div className="text-xs uppercase tracking-wider text-[#4B7A73]">{t("Allergies")}</div>
                <div className="text-sm text-[#1A332F]">{patient.allergies.join(", ") || t("None")}</div>
              </div>
              <div>
                <div className="text-xs uppercase tracking-wider text-[#4B7A73]">{t("Conditions")}</div>
                <div className="text-sm text-[#1A332F]">{patient.conditions.join(", ") || t("None")}</div>
              </div>
            </div>
          </div>
        </TabsContent>

        <TabsContent value="documents" className="pt-6">
          <div className="grid sm:grid-cols-2 gap-4">
            {documents.length === 0 && (
              <div className="col-span-2 card-soft p-10 text-center text-[#4B7A73]">{t("No documents yet. Your doctor will upload reports here.")}</div>
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
                <div className="flex items-center gap-2">
                  {d.status === "completed" && (
                    <a href={fileUrl(d.storage_path)} target="_blank" rel="noopener noreferrer"
                       className="w-10 h-10 rounded-xl bg-[#5BB9A6] hover:bg-[#4AA391] flex items-center justify-center transition-colors">
                      <Download className="w-4 h-4 text-white" />
                    </a>
                  )}
                  <button
                    type="button"
                    onClick={() => deleteDocument(d.id, d.title)}
                    disabled={deletingId === d.id}
                    title={t("Delete this record")}
                    className="w-10 h-10 rounded-xl bg-[#FCE9E9] hover:bg-[#F8D3D3] disabled:opacity-50 flex items-center justify-center transition-colors"
                  >
                    <Trash2 className="w-4 h-4 text-[#B84040]" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="upload" className="pt-6">
          <div className="card-soft p-8 max-w-2xl">
            <div className="flex items-center gap-2 mb-6">
              {[1, 2, 3].map((s, i) => (
                <div key={s} className="flex items-center gap-2">
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold transition-colors ${
                    uploadStep >= s ? "bg-[#5BB9A6] text-white" : "bg-[#D9F5EF] text-[#4B7A73]"
                  }`}>{s}</div>
                  {i < 2 && <div className={`w-12 h-0.5 ${uploadStep > s ? "bg-[#5BB9A6]" : "bg-[#D9F5EF]"}`} />}
                </div>
              ))}
            </div>

            {uploadStep === 1 && (
              <div>
                <h3 className="font-[Outfit] text-xl font-semibold text-[#2F5D57]">Document type</h3>
                <p className="text-sm text-[#4B7A73] mb-5">What kind of document are you uploading?</p>
                <div className="grid grid-cols-2 gap-3">
                  {DOC_TYPES.map((t) => (
                    <button key={t.id} onClick={() => setDocType(t.id)}
                            className={`p-4 rounded-xl text-left transition-all ${
                              docType === t.id ? "bg-[#5BB9A6] text-white" : "bg-[#F7FFFD] hover:bg-[#A7E3D4]/40 text-[#2F5D57]"
                            }`}>
                      <FileText className="w-5 h-5 mb-2" />
                      <div className="font-semibold">{t.label}</div>
                    </button>
                  ))}
                </div>
                <div className="mt-6 flex justify-end">
                  <button disabled={!docType} onClick={() => setUploadStep(2)}
                          className="px-6 py-2.5 rounded-xl bg-[#5BB9A6] text-white font-medium hover:bg-[#4AA391] disabled:opacity-50 disabled:cursor-not-allowed">
                    Continue
                  </button>
                </div>
              </div>
            )}

            {uploadStep === 2 && (
              <div>
                <h3 className="font-[Outfit] text-xl font-semibold text-[#2F5D57]">Upload file</h3>
                <p className="text-sm text-[#4B7A73] mb-5">Drag and drop, or click to browse.</p>
                <div
                  onDrop={onDrop}
                  onDragOver={(e) => e.preventDefault()}
                  onClick={() => fileInputRef.current?.click()}
                  className="border-2 border-dashed border-[#A7E3D4] bg-[#F7FFFD] hover:bg-[#D9F5EF]/50 rounded-2xl p-12 flex flex-col items-center text-center cursor-pointer transition-colors group"
                >
                  <Upload className="w-12 h-12 text-[#5BB9A6] mb-4 group-hover:scale-110 transition-transform" strokeWidth={1.5} />
                  <div className="font-semibold text-[#2F5D57]">Drop file here or click to browse</div>
                  <div className="text-xs text-[#4B7A73] mt-1">PDF, JPG, PNG up to 25 MB</div>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".pdf,.png,.jpg,.jpeg"
                    onChange={(e) => setFile(e.target.files?.[0] || null)}
                    className="hidden"
                  />
                </div>
                {file && (
                  <div className="mt-4 flex items-center gap-3 p-3 rounded-xl bg-[#A7E3D4]/30">
                    <FileText className="w-5 h-5 text-[#2F5D57]" />
                    <div className="flex-1 text-sm text-[#2F5D57]">{file.name}</div>
                    <button onClick={() => setFile(null)} className="text-[#4B7A73] hover:text-[#E05A5A]"><X className="w-4 h-4" /></button>
                  </div>
                )}
                <div className="mt-6 flex justify-between">
                  <button onClick={() => setUploadStep(1)} className="px-6 py-2.5 rounded-xl text-[#4B7A73] hover:bg-[#D9F5EF]">Back</button>
                  <button disabled={!file} onClick={() => { setUploadStep(3); handleUpload(); }}
                          className="px-6 py-2.5 rounded-xl bg-[#5BB9A6] text-white font-medium hover:bg-[#4AA391] disabled:opacity-50">
                    Upload
                  </button>
                </div>
              </div>
            )}

            {uploadStep === 3 && (
              <div className="text-center py-6">
                {uploadStatus === "uploading" && (
                  <>
                    <Loader2 className="w-10 h-10 text-[#5BB9A6] animate-spin mx-auto mb-4" />
                    <h3 className="font-[Outfit] text-xl font-semibold text-[#2F5D57]">Uploading…</h3>
                    <div className="mt-4 w-full max-w-md mx-auto h-2 rounded-full bg-[#D9F5EF] overflow-hidden">
                      <div className="h-full bg-[#5BB9A6] transition-all" style={{ width: `${uploadProgress}%` }} />
                    </div>
                    <div className="mt-2 text-xs text-[#4B7A73]">{uploadProgress}%</div>
                  </>
                )}
                {uploadStatus === "processing" && (
                  <>
                    <Loader2 className="w-10 h-10 text-[#5BB9A6] animate-spin mx-auto mb-4" />
                    <h3 className="font-[Outfit] text-xl font-semibold text-[#2F5D57]">Processing with OCR & AI…</h3>
                    <p className="text-sm text-[#4B7A73] mt-2">Extracting key insights from the document.</p>
                  </>
                )}
                {uploadStatus === "completed" && (
                  <>
                    <div className="w-14 h-14 rounded-full bg-[#5BB9A6] mx-auto flex items-center justify-center">
                      <Check className="w-7 h-7 text-white" />
                    </div>
                    <h3 className="mt-4 font-[Outfit] text-xl font-semibold text-[#2F5D57]">Upload complete</h3>
                    <p className="text-sm text-[#4B7A73] mt-2">Document was added to your record.</p>
                    <button onClick={resetUpload} className="mt-6 px-6 py-2.5 rounded-xl bg-[#5BB9A6] text-white font-medium hover:bg-[#4AA391]">
                      Upload another
                    </button>
                  </>
                )}
                {uploadStatus === "failed" && (
                  <>
                    <div className="w-14 h-14 rounded-full bg-[#E05A5A] mx-auto flex items-center justify-center">
                      <X className="w-7 h-7 text-white" />
                    </div>
                    <h3 className="mt-4 font-[Outfit] text-xl font-semibold text-[#2F5D57]">Upload failed</h3>
                    <button onClick={handleUpload} className="mt-4 inline-flex items-center gap-2 px-6 py-2.5 rounded-xl bg-[#5BB9A6] text-white font-medium hover:bg-[#4AA391]">
                      <RotateCw className="w-4 h-4" /> Retry
                    </button>
                  </>
                )}
              </div>
            )}
          </div>
        </TabsContent>

        <TabsContent value="timeline" className="pt-6">
          <div className="card-soft p-6">
            <ol className="border-l-2 border-[#A7E3D4] pl-6 space-y-6">
              {documents.length === 0 && <li className="text-sm text-[#4B7A73]">{t("Your timeline will appear here.")}</li>}
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
              <h3 className="font-[Outfit] text-lg font-semibold text-[#2F5D57]">{t("In simple terms")}</h3>
            </div>
            <p className="text-base text-[#1A332F] leading-relaxed">{patient.ai_summary}</p>
            <p className="mt-3 text-xs text-[#4B7A73] italic">{t("Educational only. Always confirm changes with your doctor.")}</p>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
