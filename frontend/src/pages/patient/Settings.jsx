import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { User, Heart, Lock, Bell } from "lucide-react";
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

const Toggle = ({ label, defaultOn, testId }) => (
  <div className="flex items-center justify-between py-2">
    <span className="text-sm text-[#1A332F]">{label}</span>
    <Switch data-testid={testId} defaultChecked={defaultOn} />
  </div>
);

export default function PatientSettings() {
  const [me, setMe] = useState(null);
  useEffect(() => { api.get("/patients").then((r) => setMe(r.data?.[0])); }, []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-[Outfit] text-3xl md:text-4xl font-bold text-[#2F5D57]">Account</h1>
        <p className="text-[#4B7A73] mt-1">Personal details and preferences.</p>
      </div>

      {me && (
        <div className="card-soft p-6 flex items-center gap-6 flex-wrap">
          <img src={me.avatar} alt={me.name} className="w-24 h-24 rounded-2xl object-cover ring-4 ring-[#A7E3D4]/40" />
          <div>
            <h2 className="font-[Outfit] text-2xl font-bold text-[#2F5D57]">{me.name}</h2>
            <p className="text-sm text-[#4B7A73]">{me.age} • {me.sex}</p>
            <p className="text-sm text-[#1A332F] mt-1">{me.email}</p>
            <p className="text-sm text-[#4B7A73]">{me.phone}</p>
          </div>
        </div>
      )}

      <div className="grid md:grid-cols-2 gap-6">
        <Section icon={User} title="Personal details">
          <div className="space-y-3 text-sm">
            <div><div className="text-xs uppercase tracking-wider text-[#4B7A73]">Date of birth</div><div className="text-[#1A332F]">January 14, 1991</div></div>
            <div><div className="text-xs uppercase tracking-wider text-[#4B7A73]">Address</div><div className="text-[#1A332F]">450 Oak Avenue, Palo Alto, CA</div></div>
            <div><div className="text-xs uppercase tracking-wider text-[#4B7A73]">Emergency contact</div><div className="text-[#1A332F]">Sam Patel · +1 555-0210</div></div>
          </div>
        </Section>
        <Section icon={Bell} title="Notifications">
          <Toggle label="Doctor replies" defaultOn testId="toggle-doctor-replies" />
          <Toggle label="New documents added" defaultOn testId="toggle-new-docs" />
          <Toggle label="AI summaries ready" testId="toggle-ai-summary-notif" />
        </Section>
        <Section icon={Lock} title="Security">
          <Toggle label="Two-factor authentication" defaultOn testId="toggle-2fa-patient" />
          <Toggle label="App lock with biometric" testId="toggle-biometric-patient" />
          <Toggle label="Session reminders" defaultOn testId="toggle-session-reminders" />
        </Section>
        <Section icon={Heart} title="Privacy">
          <Toggle label="Share data with care team" defaultOn testId="toggle-share-care-team" />
          <Toggle label="Allow research participation" testId="toggle-research" />
          <Toggle label="Anonymized analytics" defaultOn testId="toggle-analytics" />
        </Section>
      </div>
    </div>
  );
}
