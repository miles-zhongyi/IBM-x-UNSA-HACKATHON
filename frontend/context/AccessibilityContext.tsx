"use client";

import React, { createContext, useContext, useEffect, useMemo, useState } from "react";

export type FontSize = "sm" | "md" | "lg";

type Ctx = {
  dyslexiaFont: boolean;
  setDyslexiaFont: (v: boolean) => void;
  fontSize: FontSize;
  setFontSize: (v: FontSize) => void;
  offWhite: boolean;
  setOffWhite: (v: boolean) => void;
  highContrast: boolean;
  setHighContrast: (v: boolean) => void;
  voiceOutput: boolean;
  setVoiceOutput: (v: boolean) => void;
};

const AccessibilityContext = createContext<Ctx | null>(null);

export function AccessibilityProvider({ children }: { children: React.ReactNode }) {
  const [dyslexiaFont, setDyslexiaFont] = useState(false);
  const [fontSize, setFontSize] = useState<FontSize>("md");
  const [offWhite, setOffWhite] = useState(true);
  const [highContrast, setHighContrast] = useState(false);
  const [voiceOutput, setVoiceOutput] = useState(true);

  useEffect(() => {
    const root = document.documentElement;
    root.dataset.dyslexia = dyslexiaFont ? "true" : "false";
    root.dataset.fontSize = fontSize;
    root.dataset.offwhite = offWhite ? "true" : "false";
    root.dataset.highContrast = highContrast ? "true" : "false";
  }, [dyslexiaFont, fontSize, offWhite, highContrast]);

  const value = useMemo(
    () => ({
      dyslexiaFont,
      setDyslexiaFont,
      fontSize,
      setFontSize,
      offWhite,
      setOffWhite,
      highContrast,
      setHighContrast,
      voiceOutput,
      setVoiceOutput,
    }),
    [dyslexiaFont, fontSize, offWhite, highContrast, voiceOutput],
  );

  return (
    <AccessibilityContext.Provider value={value}>{children}</AccessibilityContext.Provider>
  );
}

export function useAccessibility() {
  const v = useContext(AccessibilityContext);
  if (!v) throw new Error("useAccessibility must be used within AccessibilityProvider");
  return v;
}
