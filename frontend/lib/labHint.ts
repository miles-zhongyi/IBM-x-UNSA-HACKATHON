export function extract_lab_hint(question: string): string | null {
  const q = question || "";
  if (/\bA1[Cc]\b|hemoglobin\s+A1[Cc]|hba1c/i.test(q)) return "A1C";
  if (/\bglucose\b|blood sugar/i.test(q)) return "Glucose";
  if (/\bLDL\b/i.test(q)) return "LDL";
  if (/\bHDL\b/i.test(q)) return "HDL";
  if (/\bcreatinine\b/i.test(q)) return "Creatinine";
  if (/\bTroponin\b/i.test(q)) return "Troponin";
  if (/\bBNP\b/i.test(q)) return "BNP";
  if (/\bINR\b|PT\/INR/i.test(q)) return "INR";
  return null;
}
