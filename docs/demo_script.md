# Demo script (5–7 minutes)

## Setup (before judges arrive)

1. Terminal A (repo root): `uvicorn backend.api.main:app --reload --port 8000`
2. Terminal B: `cd frontend && npm run dev`
3. Browser: `http://localhost:3000`

## 1) Patient — grounded answers (2 min)

1. Open **Patient / caregiver** → `marcus-demo`.
2. Scroll to **Ask about your records**.
3. Ask: *“What did the doctors think was wrong with my heart?”*
4. Expand a **citation pill** — show chunk text + visit date metadata.
5. Optional: ask an **A1C trend** question on `elena-demo`: *“How has my A1C changed over time?”* — show chart when API returns `trend`.

## 2) Safety (1 min)

On any patient chat, ask: *“Should I double my metformin dose?”*

- Expect **hard refusal** with `safety_triggered: true` and **no LLM path** (backend `safety.py`).

## 3) Clinician view (2 min)

1. Open **Clinician / staff**.
2. Show **demo patients** + visit list.
3. **Paste** a long snippet into **Paste visit text**, ingest, refresh patient view.
4. Open **Escalated questions** after submitting an escalation from the patient screen.

## 4) Accessibility (30–60 sec)

On patient view: toggle **OpenDyslexic**, **text size**, **high contrast**, **warm background**.

## Closing line

“This is a demo pipeline: retrieval + citations reduce hallucinations, but it does not replace clinicians or emergency services.”
