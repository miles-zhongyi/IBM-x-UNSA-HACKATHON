let API_BASE_OVERRIDE: string | null = null;

export function configureApiBase(url: string | null) {
  API_BASE_OVERRIDE = url && url.trim() ? url.trim().replace(/\/$/, "") : null;
}

function apiBase() {
  return (
    API_BASE_OVERRIDE ??
    process.env.NEXT_PUBLIC_API_BASE?.replace(/\/$/, "") ??
    "http://127.0.0.1:8000"
  );
}

export type TimelineRow = {
  id: string;
  document_type: string | null;
  visit_date: string | null;
  provider_name: string | null;
  summary: string | null;
  chief_complaint?: string | null;
};

export type ChatCitation = {
  document_id: string;
  visit_date?: string | null;
  chunk_text: string;
};

export type ChatResponse = {
  answer: string;
  citations: ChatCitation[];
  escalated: boolean;
  safety_triggered: boolean;
  trend?: Array<Record<string, unknown>> | null;
};

async function json<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(`${apiBase()}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });
  if (!r.ok) {
    const t = await r.text();
    throw new Error(t || r.statusText);
  }
  return r.json() as Promise<T>;
}

export function getApiBase() {
  return apiBase();
}

export async function ingestDocumentText(
  patientId: string,
  text: string,
  sourceLabel = "pasted",
) {
  return json<Record<string, unknown>>(`/api/patients/${patientId}/documents`, {
    method: "POST",
    body: JSON.stringify({ text, source_label: sourceLabel }),
  });
}

export async function getTimeline(patientId: string) {
  return json<TimelineRow[]>(`/api/patients/${patientId}/timeline`);
}

export async function getDiagnoses(patientId: string, activeOnly = false) {
  return json<Array<Record<string, unknown>>>(
    `/api/patients/${patientId}/diagnoses?active_only=${activeOnly ? "true" : "false"}`,
  );
}

export async function getMedications(patientId: string) {
  return json<Array<Record<string, unknown>>>(
    `/api/patients/${patientId}/medications`,
  );
}

export async function getLabs(patientId: string) {
  return json<Array<Record<string, unknown>>>(`/api/patients/${patientId}/labs`);
}

export async function getLabTrend(patientId: string, labName: string) {
  const q = new URLSearchParams({ lab_name: labName });
  return json<Array<Record<string, unknown>>>(
    `/api/patients/${patientId}/labs/trend?${q.toString()}`,
  );
}

export async function postChat(
  patientId: string,
  question: string,
  opts?: { language?: string; detailLevel?: "full" | "basic" },
) {
  return json<ChatResponse>(`/api/patients/${patientId}/chat`, {
    method: "POST",
    body: JSON.stringify({
      question,
      language: opts?.language,
      detail_level: opts?.detailLevel ?? "full",
    }),
  });
}

export async function getDocument(documentId: string) {
  return json<Record<string, unknown>>(`/api/documents/${documentId}`);
}

export async function postEscalate(
  patientId: string,
  question: string,
  context?: string,
) {
  return json<{ ticket_id: string; status: string }>(
    `/api/patients/${patientId}/escalate`,
    {
      method: "POST",
      body: JSON.stringify({ question, context }),
    },
  );
}

export async function getDoctorInbox(patientId?: string) {
  const q = patientId ? `?patient_id=${encodeURIComponent(patientId)}` : "";
  return json<Array<Record<string, unknown>>>(`/api/doctor/inbox${q}`);
}

export async function getDoctorPatients() {
  return json<Array<{ patient_id: string; visit_count: number }>>(
    `/api/doctor/patients`,
  );
}
