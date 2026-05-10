import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { Upload, FileText, Check, Loader2, X, RotateCw } from "lucide-react";
import { toast } from "sonner";
import { useUiI18n } from "@/lib/ui-i18n";

const DOC_TYPES = [
  { id: "report", label: "Lab Report" },
  { id: "scan", label: "Imaging / Scan" },
  { id: "prescription", label: "Prescription" },
  { id: "other", label: "Other" },
];

const getPatientAvatar = (name, avatar) => {
  const lower = name?.toLowerCase();
  if (lower === "dorothy price") return "https://images.pexels.com/photos/29707402/pexels-photo-29707402.jpeg";
  if (lower === "marcus hale") return "https://images.pexels.com/photos/12477590/pexels-photo-12477590.jpeg";
  if (lower === "elena ruiz") return "https://images.pexels.com/photos/8297124/pexels-photo-8297124.jpeg";
  return avatar;
};

export default function DoctorUpload() {
  const { t } = useUiI18n();
  const [step, setStep] = useState(1);
  const [patients, setPatients] = useState([]);
  const [patientId, setPatientId] = useState("");
  const [docType, setDocType] = useState("");
  const [file, setFile] = useState(null);
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState(null); // null | uploading | processing | completed | failed
  const fileInputRef = useRef(null);

  useEffect(() => {
    api.get("/patients").then((r) => setPatients(r.data || []));
  }, []);

  const reset = () => {
    setStep(1); setPatientId(""); setDocType(""); setFile(null); setProgress(0); setStatus(null);
  };

  const onDrop = (e) => {
    e.preventDefault();
    const f = e.dataTransfer.files?.[0];
    if (f) setFile(f);
  };

  const handleUpload = async () => {
    if (!file) return;
    setStatus("uploading");
    setProgress(0);
    const fd = new FormData();
    fd.append("patient_id", patientId);
    fd.append("doc_type", docType);
    fd.append("title", file.name);
    fd.append("file", file);
    try {
      await api.post("/upload", fd, {
        headers: { "Content-Type": "multipart/form-data" },
        onUploadProgress: (e) => setProgress(Math.round((e.loaded / (e.total || 1)) * 100)),
      });
      setStatus("processing");
      setTimeout(() => {
        setStatus("completed");
        toast.success(t("Document uploaded and processed"));
      }, 800);
    } catch (e) {
      console.error(e);
      setStatus("failed");
      toast.error(t("Upload failed"));
    }
  };

  const Stepper = () => (
    <div className="flex items-center gap-2 mb-6">
      {[1, 2, 3, 4].map((s, i) => (
        <div key={s} className="flex items-center gap-2">
          <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold transition-colors ${
            step >= s ? "bg-[#5BB9A6] text-white" : "bg-[#D9F5EF] text-[#4B7A73]"
          }`}>{s}</div>
          {i < 3 && <div className={`w-12 h-0.5 ${step > s ? "bg-[#5BB9A6]" : "bg-[#D9F5EF]"}`} />}
        </div>
      ))}
    </div>
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-[Outfit] text-3xl md:text-4xl font-bold text-[#2F5D57]">{t("Upload Documents")}</h1>
        <p className="text-[#4B7A73] mt-1">{t("Securely add reports, scans and prescriptions to your patient's record.")}</p>
      </div>

      <div className="card-soft p-8 max-w-3xl">
        <Stepper />

        {step === 1 && (
          <div data-testid="step-choose-patient">
            <h3 className="font-[Outfit] text-xl font-semibold text-[#2F5D57]">{t("Choose a patient")}</h3>
            <p className="text-sm text-[#4B7A73] mb-5">{t("Select who this document belongs to.")}</p>
            <div className="grid sm:grid-cols-2 gap-3">
              {patients.map((p) => (
                <button
                  key={p.id}
                  onClick={() => setPatientId(p.id)}
                  data-testid={`select-patient-${p.id}`}
                  className={`flex items-center gap-3 p-3 rounded-xl text-left transition-all ${
                    patientId === p.id ? "bg-[#5BB9A6] text-white shadow-sm" : "bg-[#F7FFFD] hover:bg-[#A7E3D4]/40"
                  }`}
                >
                  <img
                    src={getPatientAvatar(p.name, p.avatar)}
                    alt={p.name}
                    className="w-10 h-10 rounded-full object-cover"
                  />
                  <div>
                    <div className="font-semibold">{p.name}</div>
                    <div className={`text-xs ${patientId === p.id ? "text-white/80" : "text-[#4B7A73]"}`}>{p.age} • {p.sex}</div>
                  </div>
                </button>
              ))}
            </div>
            <div className="mt-6 flex justify-end">
              <button data-testid="next-step-1" disabled={!patientId} onClick={() => setStep(2)}
                      className="px-6 py-2.5 rounded-xl bg-[#5BB9A6] text-white font-medium hover:bg-[#4AA391] disabled:opacity-50 disabled:cursor-not-allowed">
                {t("Continue")}
              </button>
            </div>
          </div>
        )}

        {step === 2 && (
          <div data-testid="step-doc-type">
            <h3 className="font-[Outfit] text-xl font-semibold text-[#2F5D57]">{t("Document type")}</h3>
            <p className="text-sm text-[#4B7A73] mb-5">{t("What kind of document are you uploading?")}</p>
            <div className="grid grid-cols-2 gap-3">
              {DOC_TYPES.map((doc) => (
                <button key={doc.id} onClick={() => setDocType(doc.id)}
                        data-testid={`doctype-${doc.id}`}
                        className={`p-4 rounded-xl text-left transition-all ${
                          docType === doc.id ? "bg-[#5BB9A6] text-white" : "bg-[#F7FFFD] hover:bg-[#A7E3D4]/40 text-[#2F5D57]"
                        }`}>
                  <FileText className="w-5 h-5 mb-2" />
                  <div className="font-semibold">{t(doc.label)}</div>
                </button>
              ))}
            </div>
            <div className="mt-6 flex justify-between">
              <button onClick={() => setStep(1)} className="px-6 py-2.5 rounded-xl text-[#4B7A73] hover:bg-[#D9F5EF]">{t("Back")}</button>
              <button data-testid="next-step-2" disabled={!docType} onClick={() => setStep(3)}
                      className="px-6 py-2.5 rounded-xl bg-[#5BB9A6] text-white font-medium hover:bg-[#4AA391] disabled:opacity-50">
                {t("Continue")}
              </button>
            </div>
          </div>
        )}

        {step === 3 && (
          <div data-testid="step-file">
            <h3 className="font-[Outfit] text-xl font-semibold text-[#2F5D57]">{t("Upload file")}</h3>
            <p className="text-sm text-[#4B7A73] mb-5">{t("Drag and drop, or click to browse.")}</p>
            <div
              onDrop={onDrop}
              onDragOver={(e) => e.preventDefault()}
              onClick={() => fileInputRef.current?.click()}
              data-testid="dropzone"
              className="border-2 border-dashed border-[#A7E3D4] bg-[#F7FFFD] hover:bg-[#D9F5EF]/50 rounded-2xl p-12 flex flex-col items-center text-center cursor-pointer transition-colors group"
            >
              <Upload className="w-12 h-12 text-[#5BB9A6] mb-4 group-hover:scale-110 transition-transform" strokeWidth={1.5} />
              <div className="font-semibold text-[#2F5D57]">{t("Drop file here or click to browse")}</div>
              <div className="text-xs text-[#4B7A73] mt-1">{t("PDF, JPG, PNG up to 25 MB")}</div>
              <input
                ref={fileInputRef}
                data-testid="file-input"
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
              <button onClick={() => setStep(2)} className="px-6 py-2.5 rounded-xl text-[#4B7A73] hover:bg-[#D9F5EF]">{t("Back")}</button>
              <button data-testid="start-upload-button" disabled={!file}
                      onClick={() => { setStep(4); handleUpload(); }}
                      className="px-6 py-2.5 rounded-xl bg-[#5BB9A6] text-white font-medium hover:bg-[#4AA391] disabled:opacity-50">
                {t("Upload")}
              </button>
            </div>
          </div>
        )}

        {step === 4 && (
          <div data-testid="step-status" className="text-center py-6">
            {status === "uploading" && (
              <>
                <Loader2 className="w-10 h-10 text-[#5BB9A6] animate-spin mx-auto mb-4" />
                <h3 className="font-[Outfit] text-xl font-semibold text-[#2F5D57]">{t("Uploading…")}</h3>
                <div className="mt-4 w-full max-w-md mx-auto h-2 rounded-full bg-[#D9F5EF] overflow-hidden">
                  <div className="h-full bg-[#5BB9A6] transition-all" style={{ width: `${progress}%` }} />
                </div>
                <div className="mt-2 text-xs text-[#4B7A73]">{progress}%</div>
              </>
            )}
            {status === "processing" && (
              <>
                <Loader2 className="w-10 h-10 text-[#5BB9A6] animate-spin mx-auto mb-4" />
                <h3 className="font-[Outfit] text-xl font-semibold text-[#2F5D57]">{t("Processing with OCR & AI…")}</h3>
                <p className="text-sm text-[#4B7A73] mt-2">{t("Extracting key insights from the document.")}</p>
              </>
            )}
            {status === "completed" && (
              <>
                <div className="w-14 h-14 rounded-full bg-[#5BB9A6] mx-auto flex items-center justify-center">
                  <Check className="w-7 h-7 text-white" />
                </div>
                <h3 className="mt-4 font-[Outfit] text-xl font-semibold text-[#2F5D57]">{t("Upload complete")}</h3>
                <p className="text-sm text-[#4B7A73] mt-2">{t("Document was added to the patient's record.")}</p>
                <button data-testid="upload-another-button" onClick={reset} className="mt-6 px-6 py-2.5 rounded-xl bg-[#5BB9A6] text-white font-medium hover:bg-[#4AA391]">
                  {t("Upload another")}
                </button>
              </>
            )}
            {status === "failed" && (
              <>
                <div className="w-14 h-14 rounded-full bg-[#E05A5A] mx-auto flex items-center justify-center">
                  <X className="w-7 h-7 text-white" />
                </div>
                <h3 className="mt-4 font-[Outfit] text-xl font-semibold text-[#2F5D57]">{t("Upload failed")}</h3>
                <button onClick={handleUpload} className="mt-4 inline-flex items-center gap-2 px-6 py-2.5 rounded-xl bg-[#5BB9A6] text-white font-medium hover:bg-[#4AA391]">
                  <RotateCw className="w-4 h-4" /> {t("Retry")}
                </button>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
