from __future__ import annotations

import sqlite3
import uuid
from pathlib import Path
from typing import Any

_DB_PATH = Path(__file__).resolve().parent / "data" / "escalations.db"


def _conn():
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_escalation_db() -> None:
    conn = _conn()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS escalations (
                id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                question TEXT NOT NULL,
                context TEXT,
                status TEXT NOT NULL DEFAULT 'queued',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def create_escalation(patient_id: str, question: str, context: str | None) -> str:
    init_escalation_db()
    ticket_id = str(uuid.uuid4())
    conn = _conn()
    try:
        conn.execute(
            "INSERT INTO escalations (id, patient_id, question, context) VALUES (?, ?, ?, ?)",
            (ticket_id, patient_id, question, context or ""),
        )
        conn.commit()
    finally:
        conn.close()
    return ticket_id


def list_escalations(limit: int = 100) -> list[dict[str, Any]]:
    init_escalation_db()
    conn = _conn()
    try:
        rows = conn.execute(
            "SELECT id, patient_id, question, context, status, created_at "
            "FROM escalations ORDER BY datetime(created_at) DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
