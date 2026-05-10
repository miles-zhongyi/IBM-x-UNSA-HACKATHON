import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, fmtRelative } from "@/lib/api";
import { Search, Filter, ChevronRight } from "lucide-react";
import { useUiI18n } from "@/lib/ui-i18n";

const FILTERS = [
  { id: "all", label: "All" },
  { id: "active", label: "Active" },
  { id: "inactive", label: "Inactive" },
  { id: "unread", label: "Unread questions" },
];

const getPatientAvatar = (name, avatar) => {
  const lower = name?.toLowerCase();
  if (lower === "dorothy price") return "https://images.pexels.com/photos/29707402/pexels-photo-29707402.jpeg";
  if (lower === "marcus hale") return "https://images.pexels.com/photos/12477590/pexels-photo-12477590.jpeg";
  if (lower === "elena ruiz") return "https://images.pexels.com/photos/8297124/pexels-photo-8297124.jpeg";
  return avatar;
};

export default function DoctorPatients() {
  const { t } = useUiI18n();
  const [patients, setPatients] = useState([]);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("all");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    const params = {};
    if (search) params.search = search;
    if (filter !== "all") params.status = filter;
    api.get("/patients", { params }).then((r) => {
      setPatients(r.data || []);
      setLoading(false);
    });
  }, [search, filter]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-[Outfit] text-3xl md:text-4xl font-bold text-[#2F5D57]">{t("Patients")}</h1>
        <p className="text-[#4B7A73] mt-1">{patients.length} {t("patients in your care")}</p>
      </div>

      <div className="flex items-center gap-3 flex-wrap">
        <div className="relative flex-1 min-w-[260px]">
          <Search className="w-4 h-4 absolute left-4 top-1/2 -translate-y-1/2 text-[#4B7A73]" />
          <input
            data-testid="patients-search-input"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder={t("Search patients by name…")}
            className="w-full pl-11 pr-4 py-2.5 rounded-xl bg-[#F7FFFD] border border-[#C2EBE1] text-sm focus:outline-none focus:ring-2 focus:ring-[#5BB9A6]/40 focus:border-[#5BB9A6]"
          />
        </div>
        <div className="flex items-center gap-1.5 bg-[#D9F5EF] p-1 rounded-xl">
          <Filter className="w-4 h-4 text-[#4B7A73] mx-2" />
          {FILTERS.map((f) => (
            <button
              key={f.id}
              data-testid={`filter-${f.id}`}
              onClick={() => setFilter(f.id)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                filter === f.id ? "bg-[#5BB9A6] text-white shadow-sm" : "text-[#4B7A73] hover:text-[#2F5D57]"
              }`}
            >
              {t(f.label)}
            </button>
          ))}
        </div>
      </div>

      <div className="card-soft p-0 overflow-hidden">
        <div className="grid grid-cols-12 gap-4 px-6 py-4 bg-[#A7E3D4]/30 border-b border-[#C2EBE1] text-xs uppercase tracking-wider font-semibold text-[#2F5D57]">
          <div className="col-span-4">{t("Patient")}</div>
          <div className="col-span-1">{t("Age")}</div>
          <div className="col-span-1">{t("Sex")}</div>
          <div className="col-span-3">{t("Last activity")}</div>
          <div className="col-span-2 text-center">{t("Pending Q's")}</div>
          <div className="col-span-1 text-right">{t("Status")}</div>
        </div>
        {loading ? (
          <div className="px-6 py-12 text-center text-[#4B7A73]">{t("Loading…")}</div>
        ) : patients.length === 0 ? (
          <div className="px-6 py-12 text-center text-[#4B7A73]">{t("No patients match your filters.")}</div>
        ) : (
          patients.map((p) => (
            <Link
              key={p.id}
              to={`/doctor/patients/${p.id}`}
              data-testid={`patient-row-${p.id}`}
              className="grid grid-cols-12 gap-4 items-center px-6 py-4 border-b border-[#C2EBE1]/50 hover:bg-[#F7FFFD]/70 transition-colors group"
            >
              <div className="col-span-4 flex items-center gap-3">
                <img
                  src={getPatientAvatar(p.name, p.avatar)}
                  alt={p.name}
                  className="w-10 h-10 rounded-full object-cover ring-2 ring-[#A7E3D4]/40"
                />
                <div>
                  <div className="font-semibold text-[#2F5D57]">{p.name}</div>
                  <div className="text-xs text-[#4B7A73]">{p.email}</div>
                </div>
              </div>
              <div className="col-span-1 text-sm text-[#1A332F]">{p.age}</div>
              <div className="col-span-1 text-sm text-[#1A332F]">{p.sex}</div>
              <div className="col-span-3 text-sm text-[#4B7A73]">{fmtRelative(p.last_activity)}</div>
              <div className="col-span-2 text-center">
                {p.pending_questions > 0 ? (
                  <span className="inline-flex items-center justify-center min-w-[2rem] px-2.5 py-0.5 rounded-full bg-[#E5A832]/15 text-[#A87D0E] text-xs font-bold">
                    {p.pending_questions}
                  </span>
                ) : (
                  <span className="text-xs text-[#4B7A73]">{t("—")}</span>
                )}
              </div>
              <div className="col-span-1 flex items-center justify-end gap-2">
                <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold border ${
                  p.status === "active"
                    ? "bg-[#A7E3D4]/40 text-[#2F5D57] border-[#5BB9A6]/30"
                    : "bg-[#F7FFFD] text-[#4B7A73] border-[#C2EBE1]"
                }`}>{t(p.status)}</span>
                <ChevronRight className="w-4 h-4 text-[#4B7A73] opacity-0 group-hover:opacity-100 transition-opacity" />
              </div>
            </Link>
          ))
        )}
      </div>
    </div>
  );
}
