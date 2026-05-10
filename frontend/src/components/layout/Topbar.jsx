import { Bell, Search, ChevronDown } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

export default function Topbar({ role }) {
  const [profile, setProfile] = useState(null);
  const [notifs, setNotifs] = useState([]);

  useEffect(() => {
    if (role === "doctor") {
      api.get("/doctors/me").then((r) => setProfile(r.data)).catch(() => {});
      api.get("/activity?limit=6").then((r) => setNotifs(r.data || [])).catch(() => {});
    } else {
      // For patient portal use first patient as "me"
      api.get("/patients").then((r) => {
        const me = (r.data || [])[0];
        if (me) setProfile({ name: me.name, specialty: `${me.age} • ${me.sex}`, avatar: me.avatar });
      }).catch(() => {});
      api.get("/activity?limit=6").then((r) => setNotifs(r.data || [])).catch(() => {});
    }
  }, [role]);

  return (
    <header
      data-testid="top-navbar"
      className="glass-panel sticky top-0 z-40 h-20 flex items-center justify-between gap-6 px-6 lg:px-10"
    >
      <div className="flex-1 max-w-xl">
        <div className="relative">
          <Search className="w-4 h-4 absolute left-4 top-1/2 -translate-y-1/2 text-[#4B7A73]" strokeWidth={1.8} />
          <input
            data-testid="topbar-search-input"
            placeholder={role === "doctor" ? "Search patients, reports, queries…" : "Search records, reports…"}
            className="w-full pl-11 pr-4 py-2.5 rounded-xl bg-[#F7FFFD] border border-[#C2EBE1] text-sm text-[#1A332F] placeholder:text-[#4B7A73]/70 focus:outline-none focus:ring-2 focus:ring-[#5BB9A6]/40 focus:border-[#5BB9A6] transition-shadow"
          />
        </div>
      </div>

      <div className="flex items-center gap-4">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button
              data-testid="notifications-button"
              className="relative w-10 h-10 rounded-xl bg-[#D9F5EF] hover:bg-[#A7E3D4]/60 flex items-center justify-center transition-colors"
            >
              <Bell className="w-5 h-5 text-[#2F5D57]" strokeWidth={1.7} />
              {notifs.length > 0 && (
                <span className="absolute top-2 right-2 w-2 h-2 rounded-full bg-[#E05A5A] pulse-dot" />
              )}
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-80 bg-[#F7FFFD] border-[#C2EBE1]">
            <DropdownMenuLabel className="font-[Outfit] text-[#2F5D57]">Notifications</DropdownMenuLabel>
            <DropdownMenuSeparator />
            {notifs.length === 0 ? (
              <div className="text-sm text-[#4B7A73] px-3 py-4">You're all caught up.</div>
            ) : (
              notifs.map((n) => (
                <DropdownMenuItem key={n.id} className="flex flex-col items-start gap-0.5 py-2">
                  <span className="text-sm font-medium text-[#2F5D57]">{n.title}</span>
                  <span className="text-xs text-[#4B7A73]">{n.description}</span>
                </DropdownMenuItem>
              ))
            )}
          </DropdownMenuContent>
        </DropdownMenu>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button
              data-testid="profile-dropdown-button"
              className="flex items-center gap-3 pl-2 pr-3 py-1.5 rounded-xl hover:bg-[#D9F5EF] transition-colors"
            >
              <img
                src={role === "patient" ? "https://images.pexels.com/photos/29707402/pexels-photo-29707402.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=200&w=200" : "https://images.pexels.com/photos/4173251/pexels-photo-4173251.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=200&w=200"}
                alt="profile"
                className="w-9 h-9 rounded-full object-cover ring-2 ring-[#A7E3D4]"
              />
              <div className="text-left hidden sm:block">
                <div className="text-sm font-semibold text-[#2F5D57] leading-tight">{profile?.name || "Loading…"}</div>
                <div className="text-xs text-[#4B7A73]">{profile?.specialty || ""}</div>
              </div>
              <ChevronDown className="w-4 h-4 text-[#4B7A73]" />
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56 bg-[#F7FFFD] border-[#C2EBE1]">
            <DropdownMenuLabel className="font-[Outfit] text-[#2F5D57]">My account</DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem>Profile</DropdownMenuItem>
            <DropdownMenuItem>Preferences</DropdownMenuItem>
            <DropdownMenuItem>Help & Support</DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem className="text-[#E05A5A]">Sign out</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
