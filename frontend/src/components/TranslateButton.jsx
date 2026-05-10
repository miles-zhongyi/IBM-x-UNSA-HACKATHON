import { useState } from "react";
import { api } from "@/lib/api";
import { Languages, Loader2 } from "lucide-react";

export default function TranslateButton({ text, className = "" }) {
  const [translated, setTranslated] = useState(null);
  const [loading, setLoading] = useState(false);

  const targetLang = localStorage.getItem('inputLanguage') || 'en';

  const handleClick = async () => {
    if (translated !== null) {
      setTranslated(null);
      return;
    }
    setLoading(true);
    try {
      const r = await api.post("/translate", { text, target_lang: targetLang });
      setTranslated(r.data.translated || "");
    } catch {
      setTranslated("(translation unavailable)");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <button
        onClick={handleClick}
        disabled={loading}
        data-testid="translate-button"
        className={`mt-2 inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-medium transition-colors ${className}`}
      >
        {loading ? <Loader2 className="w-3 h-3 animate-spin" /> : <Languages className="w-3 h-3" />}
        {translated !== null ? "Show original" : `Translate`}
      </button>
      {translated !== null && (
        <div className="mt-2 text-sm leading-relaxed italic opacity-90">{translated}</div>
      )}
    </div>
  );
}
