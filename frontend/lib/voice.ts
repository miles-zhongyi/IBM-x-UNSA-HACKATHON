"use client";

type WebSpeechRecognition = {
  lang: string;
  interimResults: boolean;
  maxAlternatives: number;
  start(): void;
  stop(): void;
  onresult: ((ev: { results: { [key: number]: { [key: number]: { transcript: string } } } }) => void) | null;
  onerror: ((ev: { error?: string }) => void) | null;
  onend: (() => void) | null;
};

export function isSpeechRecognitionAvailable() {
  return typeof window !== "undefined" && ("SpeechRecognition" in window || "webkitSpeechRecognition" in window);
}

export function isSpeechSynthesisAvailable() {
  return typeof window !== "undefined" && "speechSynthesis" in window;
}

export function speakText(text: string, lang = "en-US") {
  if (!isSpeechSynthesisAvailable()) return;
  window.speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  u.lang = lang;
  u.rate = 0.95;
  window.speechSynthesis.speak(u);
}

export function stopSpeaking() {
  if (isSpeechSynthesisAvailable()) window.speechSynthesis.cancel();
}

export type RecognitionHandlers = {
  onResult: (text: string) => void;
  onError?: (message: string) => void;
  onEnd?: () => void;
};

export function startRecognition(
  handlers: RecognitionHandlers,
  lang = "en-US",
): (() => void) | null {
  if (!isSpeechRecognitionAvailable()) {
    handlers.onError?.("Speech recognition is not supported in this browser.");
    return null;
  }
  const win = window as unknown as {
    SpeechRecognition?: new () => WebSpeechRecognition;
    webkitSpeechRecognition?: new () => WebSpeechRecognition;
  };
  const SR = win.SpeechRecognition ?? win.webkitSpeechRecognition;
  if (!SR) return null;

  const rec = new SR();
  rec.lang = lang;
  rec.interimResults = false;
  rec.maxAlternatives = 1;
  rec.onresult = (ev) => {
    const text = ev.results[0]?.[0]?.transcript?.trim() ?? "";
    if (text) handlers.onResult(text);
  };
  rec.onerror = (ev) => handlers.onError?.(ev.error ?? "recognition error");
  rec.onend = () => handlers.onEnd?.();
  rec.start();
  return () => {
    try {
      rec.stop();
    } catch {
      /* ignore */
    }
  };
}
