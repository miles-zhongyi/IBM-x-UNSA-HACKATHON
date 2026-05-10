import { Link } from "react-router-dom";
import { Stethoscope, HeartPulse, ArrowRight, Heart, Activity } from "lucide-react";
import { useUiI18n } from "@/lib/ui-i18n";

export default function Landing() {
  const { t } = useUiI18n();
  return (
    <div className="min-h-screen bg-[#F7FFFD] relative overflow-hidden">
      <div className="absolute -top-40 -right-40 w-[40rem] h-[40rem] rounded-full bg-[#A7E3D4]/40 blur-3xl pointer-events-none" />
      <div className="absolute -bottom-40 -left-40 w-[40rem] h-[40rem] rounded-full bg-[#D9F5EF]/80 blur-3xl pointer-events-none" />

      <header className="relative z-10 max-w-7xl mx-auto px-8 py-6 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-[#5BB9A6] flex items-center justify-center shadow-sm">
            <Activity className="w-5 h-5 text-white" />
          </div>
          <span className="font-[Outfit] font-bold text-xl text-[#2F5D57]">MyHealthVoice AI</span>
        </div>
      </header>

      <section className="relative z-10 max-w-7xl mx-auto px-8 pt-12 pb-20 text-center">
        <span className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-[#D9F5EF] text-[#2F5D57] text-xs font-semibold tracking-wider">
          <Heart className="w-3.5 h-3.5 text-[#5BB9A6]" strokeWidth={2} fill="none" /> {t("MyHealthVoice Platform")}
        </span>
        <h1 className="mt-6 font-[Outfit] font-extrabold text-4xl sm:text-5xl lg:text-6xl tracking-tight max-w-5xl mx-auto leading-[1.05]">
          <span className="text-[#2F5D57]">{t("Welcome to")} </span>
          <span className="text-[#5BB9A6]">MyHealthVoice</span>
        </h1>
        <p className="mt-5 text-base sm:text-lg text-[#4B7A73] max-w-2xl mx-auto leading-relaxed">
          {t("Select your portal to get started with your healthcare journey.")}
        </p>

        <div className="mt-12 grid sm:grid-cols-2 gap-6 max-w-4xl mx-auto">
          <Link
            to="/doctor"
            data-testid="enter-doctor-portal"
            className="card-soft p-8 text-left group"
          >
            <div className="flex items-center justify-between">
              <div className="w-14 h-14 rounded-2xl bg-[#5BB9A6] flex items-center justify-center shadow-sm">
                <Stethoscope className="w-7 h-7 text-white" strokeWidth={1.7} />
              </div>
              <ArrowRight className="w-5 h-5 text-[#2F5D57] group-hover:translate-x-1 transition-transform" />
            </div>
            <h3 className="mt-6 font-[Outfit] font-semibold text-2xl text-[#2F5D57]">{t("Doctor Portal")}</h3>
            <p className="mt-2 text-sm text-[#4B7A73] leading-relaxed">
              {t("Manage patients, review uploads, answer queries and get AI-assisted reply drafts — all in one workspace.")}
            </p>
            <div className="mt-6 flex flex-wrap gap-2">
              {["Dashboard", "Patients", "Uploads", "Queries"].map((label) => (
                <span key={label} className="text-xs px-3 py-1 rounded-full bg-[#A7E3D4]/40 text-[#2F5D57]">{t(label)}</span>
              ))}
            </div>
          </Link>

          <Link
            to="/patient"
            data-testid="enter-patient-portal"
            className="card-soft p-8 text-left group"
          >
            <div className="flex items-center justify-between">
              <div className="w-14 h-14 rounded-2xl bg-[#2F5D57] flex items-center justify-center shadow-sm">
                <HeartPulse className="w-7 h-7 text-white" strokeWidth={1.7} />
              </div>
              <ArrowRight className="w-5 h-5 text-[#2F5D57] group-hover:translate-x-1 transition-transform" />
            </div>
            <h3 className="mt-6 font-[Outfit] font-semibold text-2xl text-[#2F5D57]">{t("Patient Portal")}</h3>
            <p className="mt-2 text-sm text-[#4B7A73] leading-relaxed">
              {t("Read your reports in plain language, chat with an educational AI, and reach your doctor with a single message.")}
            </p>
            <div className="mt-6 flex flex-wrap gap-2">
              {["AI Assistant", "Health Records", "Ask Doctor", "Timeline"].map((label) => (
                <span key={label} className="text-xs px-3 py-1 rounded-full bg-[#A7E3D4]/40 text-[#2F5D57]">{t(label)}</span>
              ))}
            </div>
          </Link>
        </div>

      </section>
    </div>
  );
}
