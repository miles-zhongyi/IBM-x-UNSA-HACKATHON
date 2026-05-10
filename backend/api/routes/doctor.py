from __future__ import annotations

from fastapi import APIRouter, Query

from backend.ingestion.storage import get_patient_timeline

from ..escalation_store import list_escalations

router = APIRouter()

DEMO_PATIENT_IDS = ("marcus-demo", "elena-demo", "dorothy-demo")


@router.get("/patients")
def list_patients_with_visit_counts() -> list[dict]:
    """Demo doctor dashboard: known personas + visit counts from timeline."""
    out: list[dict] = []
    for pid in DEMO_PATIENT_IDS:
        timeline = get_patient_timeline(pid)
        out.append({"patient_id": pid, "visit_count": len(timeline)})
    return out


@router.get("/inbox")
def doctor_inbox(
    patient_id: str | None = Query(
        None,
        description="Optional filter (demo: omit to see all escalations).",
    ),
) -> list[dict]:
    rows = list_escalations(limit=200)
    if patient_id:
        return [r for r in rows if r.get("patient_id") == patient_id]
    return rows
