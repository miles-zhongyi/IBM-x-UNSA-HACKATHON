import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Bell, Lock, Sparkles, Palette } from "lucide-react";
import { Switch } from "@/components/ui/switch";

const Section = ({ icon: Icon, title, children }) => (
  <div className="card-soft p-6">
    <div className="flex items-center gap-2 mb-4">
      <Icon className="w-5 h-5 text-[#5BB9A6]" />
      <h3 className="font-[Outfit] text-lg font-semibold text-[#2F5D57]">{title}</h3>
    </div>
    {children}
  </div>
);

const Toggle = ({ label, defaultOn = false, testId }) => (
  <div className="flex items-center justify-between py-2">
    <span className="text-sm text-[#1A332F]">{label}</span>
    <Switch data-testid={testId} defaultChecked={defaultOn} />
  </div>
);

export default function DoctorSettings() {
  const [doctor, setDoctor] = useState(null);
  useEffect(() => { api.get("/doctors/me").then((r) => setDoctor(r.data)); }, []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-[Outfit] text-3xl md:text-4xl font-bold text-[#2F5D57]">Account</h1>
        <p className="text-[#4B7A73] mt-1">Manage your profile and preferences.</p>
      </div>

      {doctor && (
        <div className="card-soft p-6 flex items-center gap-6 flex-wrap">
          <img src={doctor.avatar} alt={doctor.name} className="w-24 h-24 rounded-2xl object-cover ring-4 ring-[#A7E3D4]/40" />
          <div className="flex-1 min-w-[200px]">
            <h2 className="font-[Outfit] text-2xl font-bold text-[#2F5D57]">{doctor.name}</h2>
            <p className="text-sm text-[#4B7A73]">{doctor.specialty}</p>
            <p className="text-sm text-[#1A332F] mt-2">{doctor.qualifications}</p>
            <p className="text-sm text-[#4B7A73] mt-1">{doctor.clinic}</p>
          </div>
          <div className="flex flex-col gap-1 text-sm text-[#4B7A73]">
            <span>{doctor.email}</span>
            <span>{doctor.phone}</span>
          </div>
        </div>
      )}

      <div className="grid md:grid-cols-2 gap-6">
        <Section icon={Bell} title="Notifications">
          <Toggle label="Email me on new patient questions" defaultOn testId="toggle-email-questions" />
          <Toggle label="SMS for urgent queries" testId="toggle-sms-urgent" />
          <Toggle label="Daily digest" defaultOn testId="toggle-daily-digest" />
        </Section>
        <Section icon={Lock} title="Security">
          <Toggle label="Two-factor authentication" defaultOn testId="toggle-2fa" />
          <Toggle label="Sign out idle sessions" defaultOn testId="toggle-idle-sessions" />
          <Toggle label="Require biometric for downloads" testId="toggle-biometric" />
        </Section>
        <Section icon={Sparkles} title="AI Preferences">
          <Toggle label="AI-suggested replies" defaultOn testId="toggle-ai-replies" />
          <Toggle label="AI-generated patient summaries" defaultOn testId="toggle-ai-summaries" />
          <Toggle label="Flag inconsistent AI responses" defaultOn testId="toggle-ai-flagging" />
        </Section>
        <Section icon={Palette} title="Appearance">
          <Toggle label="Dense table view" testId="toggle-dense-view" />
          <Toggle label="Reduce motion" testId="toggle-reduce-motion" />
          <Toggle label="Show avatars" defaultOn testId="toggle-avatars" />
        </Section>
      </div>
    </div>
  );
}
