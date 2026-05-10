"use client";

import { useState } from "react";
import { ingestDocumentText } from "@/lib/api";

const DEMO_IDS = ["marcus-demo", "elena-demo", "dorothy-demo"] as const;

export function NoteIntake() {
  const [patientId, setPatientId] = useState<(typeof DEMO_IDS)[number]>("marcus-demo");
  const [text, setText] = useState("");
  const [status, setStatus] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit() {
    setBusy(true);
    setStatus(null);
    try {
      const res = await ingestDocumentText(patientId, text, "doctor_paste");
      setStatus(JSON.stringify(res, null, 2));
    } catch (e) {
      setStatus(String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="rounded-2xl border border-[var(--line)] bg-[var(--card)] p-4 shadow-sm">
      <h2 className="text-lg font-semibold">Paste visit text</h2>
      <div className="mt-4 flex flex-col gap-3">
        <label className="text-sm font-medium">
          Patient
          <select
            className="mt-1 w-full rounded-xl border border-[var(--line)] bg-[var(--bg)] p-3 text-base"
            value={patientId}
            onChange={(e) => setPatientId(e.target.value as (typeof DEMO_IDS)[number])}
          >
            {DEMO_IDS.map((id) => (
              <option key={id} value={id}>
                {id}
              </option>
            ))}
          </select>
        </label>
        <textarea
          className="min-h-[200px] w-full rounded-xl border border-[var(--line)] bg-[var(--bg)] p-3 text-base"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Paste clinical note (50+ characters)…"
        />
        <button
          type="button"
          className="min-h-touch rounded-xl bg-blue-600 px-5 py-3 text-base font-semibold text-white"
          onClick={submit}
          disabled={busy}
        >
          {busy ? "Saving…" : "Ingest note"}
        </button>
        {status && (
          <pre className="max-h-64 overflow-auto rounded-xl bg-black/5 p-3 text-xs">{status}</pre>
        )}
      </div>
    </section>
  );
}
