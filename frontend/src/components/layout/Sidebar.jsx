import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  Users,
  UploadCloud,
  MessageSquare,
  Settings,
  Activity,
  Sparkles,
  FileHeart,
  Stethoscope,
  HeartPulse,
  ChevronLeft,
} from "lucide-react";
import { useState } from "react";
import { cn } from "@/lib/utils";
import { useUiI18n } from "@/lib/ui-i18n";

const doctorNav = [
  { to: "/doctor/dashboard", icon: LayoutDashboard, label: "Dashboard" },
  { to: "/doctor/patients", icon: Users, label: "Patients" },
  { to: "/doctor/upload", icon: UploadCloud, label: "Upload Documents" },
  { to: "/doctor/queries", icon: MessageSquare, label: "Patient Queries" },
  { to: "/doctor/settings", icon: Settings, label: "Account" },
];

const patientNav = [
  { to: "/patient/dashboard", icon: HeartPulse, label: "Home" },
  { to: "/patient/ai-assistant", icon: Sparkles, label: "AI Assistant" },
  { to: "/patient/records", icon: FileHeart, label: "Health Records" },
  { to: "/patient/ask-doctor", icon: MessageSquare, label: "Ask Doctor" },
  { to: "/patient/settings", icon: Settings, label: "Account" },
];

export default function Sidebar({ role }) {
  const [collapsed, setCollapsed] = useState(false);
  const { t } = useUiI18n();
  const items = role === "doctor" ? doctorNav : patientNav;
  const Icon = role === "doctor" ? Stethoscope : HeartPulse;

  return (
    <aside
      data-testid="sidebar"
      className={cn(
        "h-screen sticky top-0 flex flex-col border-r border-[#C2EBE1] bg-[#F7FFFD] transition-all duration-300",
        collapsed ? "w-20" : "w-64"
      )}
    >
      <div className="px-5 py-6 flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-[#5BB9A6] flex items-center justify-center shadow-sm">
          <Icon className="w-5 h-5 text-white" strokeWidth={2} />
        </div>
        {!collapsed && (
          <div>
            <div className="font-[Outfit] font-bold text-[#2F5D57] text-lg leading-tight">MyHealthVoice AI</div>
            <div className="text-xs text-[#4B7A73] capitalize">{role} {t("Portal")}</div>
          </div>
        )}
      </div>

      <nav className="flex-1 px-3 py-2 space-y-1">
        {items.map((it) => (
          <NavLink
            key={it.to}
            to={it.to}
            data-testid={`nav-${it.label.toLowerCase().replace(/\s+/g, "-")}`}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all group",
                isActive
                  ? "bg-[#D9F5EF] text-[#2F5D57] shadow-sm"
                  : "text-[#4B7A73] hover:bg-[#D9F5EF]/60 hover:text-[#2F5D57]"
              )
            }
          >
            <it.icon className="w-5 h-5 shrink-0" strokeWidth={1.7} />
            {!collapsed && <span>{t(it.label)}</span>}
          </NavLink>
        ))}
      </nav>

      <div className="p-3 border-t border-[#C2EBE1]">
        <button
          onClick={() => setCollapsed((c) => !c)}
          data-testid="sidebar-collapse-button"
          className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-xl text-xs font-medium text-[#4B7A73] hover:bg-[#D9F5EF] transition-colors"
        >
          <ChevronLeft className={cn("w-4 h-4 transition-transform", collapsed && "rotate-180")} />
          {!collapsed && <span>{t("Collapse")}</span>}
        </button>
        {!collapsed && (
          <NavLink
            to="/"
            data-testid="switch-portal-button"
            className="mt-2 w-full flex items-center justify-center gap-2 px-3 py-2 rounded-xl text-xs font-medium text-[#2F5D57] bg-[#A7E3D4]/40 hover:bg-[#A7E3D4]/70 transition-colors"
          >
            <Activity className="w-3.5 h-3.5" />
            {t("Switch Portal")}
          </NavLink>
        )}
      </div>
    </aside>
  );
}
