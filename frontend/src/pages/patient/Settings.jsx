import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { User, Heart, Lock, Bell } from "lucide-react";
import { Switch } from "@/components/ui/switch";
import { useUiI18n } from "@/lib/ui-i18n";

const Section = ({ icon: Icon, title, children, t }) => (
  <div className="card-soft p-6">
    <div className="flex items-center gap-2 mb-4">
      <Icon className="w-5 h-5 text-[#5BB9A6]" />
      <h3 className="font-[Outfit] text-lg font-semibold text-[#2F5D57]">{t(title)}</h3>
    </div>
    {children}
  </div>
);

const Toggle = ({ label, defaultOn, testId, t }) => (
  <div className="flex items-center justify-between py-2">
    <span className="text-sm text-[#1A332F]">{t(label)}</span>
    <Switch data-testid={testId} defaultChecked={defaultOn} />
  </div>
);

export default function PatientSettings() {
  const { t } = useUiI18n();
  const [me, setMe] = useState(null);
  useEffect(() => { api.get("/patients").then((r) => setMe(r.data?.[0])); }, []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-[Outfit] text-3xl md:text-4xl font-bold text-[#2F5D57]">{t("Account")}</h1>
        <p className="text-[#4B7A73] mt-1">{t("Personal details and preferences.")}</p>
      </div>

      {me && (
        <div className="card-soft p-6 flex items-center gap-6 flex-wrap">
          <img
            src="https://images.pexels.com/photos/29707402/pexels-photo-29707402.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=200&w=200"
            alt={me.name}
            className="w-24 h-24 rounded-2xl object-cover ring-4 ring-[#A7E3D4]/40"
          />
          <div>
            <h2 className="font-[Outfit] text-2xl font-bold text-[#2F5D57]">{me.name}</h2>
            <p className="text-sm text-[#4B7A73]">{me.age} • {me.sex}</p>
            <p className="text-sm text-[#1A332F] mt-1">{me.email}</p>
            <p className="text-sm text-[#4B7A73]">{me.phone}</p>
          </div>
        </div>
      )}

      <div className="grid md:grid-cols-2 gap-6">
        <Section icon={User} title="Personal details" t={t}>
          <div className="space-y-3 text-sm">
            <div><div className="text-xs uppercase tracking-wider text-[#4B7A73]">{t("Date of birth")}</div><div className="text-[#1A332F]">{t("January 14, 1991")}</div></div>
            <div><div className="text-xs uppercase tracking-wider text-[#4B7A73]">{t("Address")}</div><div className="text-[#1A332F]">{t("450 Oak Avenue, Palo Alto, CA")}</div></div>
            <div><div className="text-xs uppercase tracking-wider text-[#4B7A73]">{t("Emergency contact")}</div><div className="text-[#1A332F]">{t("Sam Patel · +1 555-0210")}</div></div>
          </div>
        </Section>
        <Section icon={Bell} title="Notifications" t={t}>
          <Toggle label="Doctor replies" defaultOn testId="toggle-doctor-replies" t={t} />
          <Toggle label="New documents added" defaultOn testId="toggle-new-docs" t={t} />
          <Toggle label="AI summaries ready" testId="toggle-ai-summary-notif" t={t} />
        </Section>
        <Section icon={Lock} title="Security" t={t}>
          <Toggle label="Two-factor authentication" defaultOn testId="toggle-2fa-patient" t={t} />
          <Toggle label="App lock with biometric" testId="toggle-biometric-patient" t={t} />
          <Toggle label="Session reminders" defaultOn testId="toggle-session-reminders" t={t} />
        </Section>
        <Section icon={Heart} title="Privacy" t={t}>
          <Toggle label="Share data with care team" defaultOn testId="toggle-share-care-team" t={t} />
          <Toggle label="Allow research participation" testId="toggle-research" t={t} />
          <Toggle label="Anonymized analytics" defaultOn testId="toggle-analytics" t={t} />
        </Section>
      </div>
    </div>
  );
}
