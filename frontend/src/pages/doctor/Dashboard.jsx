import { useEffect, useState } from "react";
import { api, fmtRelative } from "@/lib/api";
import { Users, MessageSquare, AlertTriangle, FileUp, FileX2, TrendingUp, Sparkles, Activity } from "lucide-react";
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";

const StatCard = ({ icon: Icon, label, value, accent }) => (
  <div data-testid={`stat-${label.toLowerCase().replace(/\s+/g, "-")}`} className="card-soft p-6 animate-fade-up">
    <div className="flex items-start justify-between">
      <div>
        <div className="text-xs uppercase tracking-wider text-[#4B7A73] font-semibold">{label}</div>
        <div className="mt-3 font-[Outfit] text-4xl font-bold text-[#2F5D57]">{value}</div>
      </div>
      <div className={`w-11 h-11 rounded-xl flex items-center justify-center ${accent}`}>
        <Icon className="w-5 h-5 text-white" strokeWidth={1.8} />
      </div>
    </div>
  </div>
);

export default function DoctorDashboard() {
  const [data, setData] = useState(null);

  useEffect(() => {
    api.get("/dashboard/doctor").then((r) => setData(r.data));
  }, []);

  if (!data) {
    return (
      <div className="space-y-6">
        <div className="card-soft h-32 animate-pulse" />
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="card-soft h-32 animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  const { stats, alerts, activity, trend } = data;

  return (
    <div className="space-y-8">
      <div data-testid="dashboard-header" className="flex items-end justify-between flex-wrap gap-4">
        <div>
          <h1 className="font-[Outfit] text-3xl md:text-4xl font-bold text-[#2F5D57]">Good morning, Dr. Chen</h1>
          <p className="text-[#4B7A73] mt-1">Here's an overview of your practice today.</p>
        </div>
        <div className="flex items-center gap-2 text-sm text-[#4B7A73] bg-[#D9F5EF] px-3 py-1.5 rounded-full">
          <Activity className="w-4 h-4 text-[#5BB9A6]" /> {new Date().toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric" })}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-5">
        <StatCard icon={Users} label="Total Patients" value={stats.total_patients} accent="bg-[#5BB9A6]" />
        <StatCard icon={MessageSquare} label="Pending Questions" value={stats.pending_questions} accent="bg-[#2F5D57]" />
        <StatCard icon={AlertTriangle} label="Urgent Queries" value={stats.urgent_queries} accent="bg-[#E05A5A]" />
        <StatCard icon={FileUp} label="Recent Uploads" value={stats.recent_uploads} accent="bg-[#5BB9A6]" />
        <StatCard icon={FileX2} label="Failed Uploads" value={stats.failed_uploads} accent="bg-[#E5A832]" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 card-soft p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="font-[Outfit] text-xl font-semibold text-[#2F5D57]">Patient Activity</h3>
              <p className="text-xs text-[#4B7A73]">Messages and uploads across the past week</p>
            </div>
            <div className="flex items-center gap-1.5 text-sm text-[#5BB9A6] font-medium">
              <TrendingUp className="w-4 h-4" /> +12.4%
            </div>
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trend}>
                <CartesianGrid stroke="#C2EBE1" strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="day" stroke="#4B7A73" fontSize={12} tickLine={false} axisLine={false} />
                <YAxis stroke="#4B7A73" fontSize={12} tickLine={false} axisLine={false} />
                <Tooltip contentStyle={{ background: "#F7FFFD", border: "1px solid #C2EBE1", borderRadius: 12 }} />
                <Line type="monotone" dataKey="messages" stroke="#5BB9A6" strokeWidth={2.5} dot={{ r: 4, fill: "#5BB9A6" }} />
                <Line type="monotone" dataKey="uploads" stroke="#2F5D57" strokeWidth={2.5} dot={{ r: 4, fill: "#2F5D57" }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="card-soft p-6">
          <h3 className="font-[Outfit] text-xl font-semibold text-[#2F5D57]">Upload Stats</h3>
          <p className="text-xs text-[#4B7A73] mb-3">Last 7 days</p>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={trend}>
                <CartesianGrid stroke="#C2EBE1" strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="day" stroke="#4B7A73" fontSize={12} tickLine={false} axisLine={false} />
                <YAxis stroke="#4B7A73" fontSize={12} tickLine={false} axisLine={false} />
                <Tooltip contentStyle={{ background: "#F7FFFD", border: "1px solid #C2EBE1", borderRadius: 12 }} />
                <Bar dataKey="uploads" fill="#5BB9A6" radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div data-testid="alerts-panel" className="card-soft p-6">
          <div className="flex items-center gap-2 mb-4">
            <AlertTriangle className="w-5 h-5 text-[#E05A5A]" />
            <h3 className="font-[Outfit] text-xl font-semibold text-[#2F5D57]">Alerts</h3>
          </div>
          {alerts.length === 0 ? (
            <p className="text-sm text-[#4B7A73] py-6 text-center">No alerts. Everything looks good.</p>
          ) : (
            <ul className="space-y-3">
              {alerts.map((a) => (
                <li key={a.id} className="flex items-start gap-3 p-3 rounded-xl bg-[#F7FFFD]">
                  <div className={`w-2 h-2 rounded-full mt-2 ${a.severity === "error" ? "bg-[#E05A5A]" : "bg-[#E5A832]"}`} />
                  <div className="flex-1">
                    <div className="text-sm font-semibold text-[#2F5D57]">{a.title}</div>
                    <div className="text-xs text-[#4B7A73]">{a.description}</div>
                  </div>
                  <span className="text-xs text-[#4B7A73] shrink-0">{fmtRelative(a.created_at)}</span>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div data-testid="activity-panel" className="card-soft p-6">
          <div className="flex items-center gap-2 mb-4">
            <Sparkles className="w-5 h-5 text-[#5BB9A6]" />
            <h3 className="font-[Outfit] text-xl font-semibold text-[#2F5D57]">Recent Activity</h3>
          </div>
          <ul className="space-y-3">
            {activity.slice(0, 6).map((a) => (
              <li key={a.id} className="flex items-start gap-3 p-3 rounded-xl hover:bg-[#F7FFFD] transition-colors">
                <div className="w-9 h-9 rounded-xl bg-[#A7E3D4]/40 flex items-center justify-center shrink-0">
                  {a.kind === "upload" ? <FileUp className="w-4 h-4 text-[#2F5D57]" /> :
                    a.kind === "ai_summary" ? <Sparkles className="w-4 h-4 text-[#2F5D57]" /> :
                      <MessageSquare className="w-4 h-4 text-[#2F5D57]" />}
                </div>
                <div className="flex-1">
                  <div className="text-sm font-semibold text-[#2F5D57]">{a.title}</div>
                  <div className="text-xs text-[#4B7A73]">{a.description}</div>
                </div>
                <span className="text-xs text-[#4B7A73] shrink-0">{fmtRelative(a.created_at)}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
