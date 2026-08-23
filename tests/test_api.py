import os

import pytest
from fastapi.testclient import TestClient

# Must set before importing app so middleware picks up the test key
os.environ.setdefault("API_KEY", "test-api-key")

from app.main import app
from app.database import init_db
import app.security as security_mod

security_mod.API_KEY = "test-api-key"

client = TestClient(app)

AUTH = {"X-API-Key": "test-api-key"}
ACTOR = {"x-actor": "tester", **AUTH}


@pytest.fixture(autouse=True)
def setup_db(tmp_path, monkeypatch):
    db = str(tmp_path / "test.db")
    monkeypatch.setenv("DB_PATH", db)
    import app.database as db_mod

    db_mod.DB_PATH = db
    init_db()
    yield


def test_health_public():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_summary_requires_api_key():
    r = client.get("/summary")
    assert r.status_code == 401


def test_summary_empty():
    r = client.get("/summary", headers=AUTH)
    assert r.status_code == 200
    data = r.json()
    assert data["total_cases"] == 0


def test_invalid_api_key():
    r = client.get("/summary", headers={"X-API-Key": "wrong"})
    assert r.status_code == 401


def test_create_and_get_case():
    payload = {
        "title": "Test DI case",
        "system": "LIMS-01",
        "signal_type": "audit_finding",
        "opened_by": "tester",
    }
    r = client.post("/cases", json=payload, headers=ACTOR)
    assert r.status_code == 201
    case_id = r.json()["id"]
    r2 = client.get(f"/cases/{case_id}", headers=AUTH)
    assert r2.status_code == 200
    assert r2.json()["title"] == "Test DI case"


def test_create_case_missing_actor():
    payload = {
        "title": "No actor",
        "system": "SYS",
        "signal_type": "data_gap",
        "opened_by": "tester",
    }
    r = client.post("/cases", json=payload, headers=AUTH)
    assert r.status_code == 422


def test_create_case_missing_api_key():
    payload = {
        "title": "No key",
        "system": "SYS",
        "signal_type": "data_gap",
        "opened_by": "tester",
    }
    r = client.post("/cases", json=payload, headers={"x-actor": "tester"})
    assert r.status_code == 401


def test_alcoa_gap():
    payload = {
        "title": "ALCOA test",
        "system": "SYS",
        "signal_type": "audit_finding",
        "opened_by": "tester",
    }
    case_id = client.post("/cases", json=payload, headers=ACTOR).json()["id"]
    gap = {
        "attribute": "Attributable",
        "gap_found": True,
        "observation": "Actor field blank",
        "assessed_by": "tester",
    }
    r = client.post(f"/cases/{case_id}/alcoa-gaps", json=gap, headers=ACTOR)
    assert r.status_code == 201
    assert r.json()["gap_found"] is True


def test_evidence():
    case_id = client.post(
        "/cases",
        json={
            "title": "Ev test",
            "system": "SYS",
            "signal_type": "data_gap",
            "opened_by": "tester",
        },
        headers=ACTOR,
    ).json()["id"]
    ev = {
        "evidence_type": "audit_trail_review",
        "description": "Reviewed 30-day export",
        "recorded_by": "tester",
    }
    r = client.post(f"/cases/{case_id}/evidence", json=ev, headers=ACTOR)
    assert r.status_code == 201


def test_capa():
    case_id = client.post(
        "/cases",
        json={
            "title": "CAPA test",
            "system": "SYS",
            "signal_type": "data_gap",
            "opened_by": "tester",
        },
        headers=ACTOR,
    ).json()["id"]
    capa = {
        "action_type": "corrective",
        "description": "Fix the actor field in LIMS config",
        "owner": "tester",
        "due_date": "2026-12-01",
    }
    r = client.post(f"/cases/{case_id}/capas", json=capa, headers=ACTOR)
    assert r.status_code == 201
    assert r.json()["status"] == "open"


def test_audit_log():
    client.post(
        "/cases",
        json={
            "title": "Audit test",
            "system": "SYS",
            "signal_type": "audit_finding",
            "opened_by": "tester",
        },
        headers=ACTOR,
    )
    r = client.get("/audit-log", headers=AUTH)
    assert r.status_code == 200
    assert len(r.json()) >= 1


def test_case_not_found():
    r = client.get("/cases/99999", headers=AUTH)
    assert r.status_code == 404


def test_summary_after_creates():
    for i in range(3):
        client.post(
            "/cases",
            json={
                "title": f"Case {i}",
                "system": "SYS",
                "signal_type": "audit_finding",
                "opened_by": "tester",
            },
            headers=ACTOR,
        )
    r = client.get("/summary", headers=AUTH)
    assert r.json()["total_cases"] == 3


def test_rate_limit_headers_present():
    r = client.get("/summary", headers=AUTH)
    assert r.status_code == 200
    assert "X-RateLimit-Limit" in r.headers
    assert "X-RateLimit-Remaining" in r.headers
