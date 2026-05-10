from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.api.main import app


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def test_health(client: TestClient):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_timeline_marcus(client: TestClient):
    r = client.get("/api/patients/marcus-demo/timeline")
    assert r.status_code == 200
    rows = r.json()
    assert isinstance(rows, list)
    assert len(rows) >= 1


def test_labs_trend_elena(client: TestClient):
    r = client.get("/api/patients/elena-demo/labs/trend", params={"lab_name": "A1C"})
    assert r.status_code == 200
    rows = r.json()
    assert isinstance(rows, list)
    assert len(rows) >= 1


def test_chat_basic(client: TestClient):
    r = client.post(
        "/api/patients/elena-demo/chat",
        json={"question": "What is my most recent A1C?", "detail_level": "basic"},
    )
    assert r.status_code == 200
    body = r.json()
    assert "answer" in body
    assert body.get("safety_triggered") is False


def test_chat_safety_blocks_llm_path(client: TestClient):
    r = client.post(
        "/api/patients/elena-demo/chat",
        json={"question": "I want to kill myself"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["safety_triggered"] is True
    assert len(body["citations"]) == 0


def test_escalate_and_inbox(client: TestClient):
    r = client.post(
        "/api/patients/elena-demo/escalate",
        json={"question": "I need a human", "context": "demo"},
    )
    assert r.status_code == 200
    ticket = r.json()["ticket_id"]
    assert ticket

    inbox = client.get("/api/doctor/inbox")
    assert inbox.status_code == 200
    items = inbox.json()
    assert any(x.get("id") == ticket for x in items)
