"use client";

import { useState } from "react";
import type { ChatCitation } from "@/lib/api";

export function CitationPill({ c, index }: { c: ChatCitation; index: number }) {
  const [open, setOpen] = useState(false);
  const label =
    c.visit_date && c.visit_date !== "null"
      ? `Visit ${c.visit_date}`
      : `Source ${index + 1}`;
  return (
    <div className="inline-flex flex-col gap-1">
      <button
        type="button"
        className="min-h-touch rounded-full border border-[var(--line)] bg-[var(--card)] px-3 py-2 text-sm font-medium text-blue-800"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        {label}
      </button>
      {open && (
        <div className="max-w-prose rounded-xl border border-[var(--line)] bg-[var(--card)] p-3 text-sm text-[var(--muted)]">
          <div className="mb-1 text-xs text-[var(--fg)]">document_id: {c.document_id || "—"}</div>
          <div className="whitespace-pre-wrap">{c.chunk_text}</div>
        </div>
      )}
    </div>
  );
}
