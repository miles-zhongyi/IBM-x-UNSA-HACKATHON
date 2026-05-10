from __future__ import annotations

from fastapi import APIRouter, Query

from ..escalation_store import list_escalations

router = APIRouter()


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
