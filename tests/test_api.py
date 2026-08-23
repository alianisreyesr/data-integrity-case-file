import os

import pytest
from fastapi.testclient import TestClient

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


def _create_case(title="Test DI case"):
    payload = {
        "title": title,
        "system": "LIMS-01",
        "signal_type": "audit_finding",
        "opened_by": "tester",
    }
    r = client.post("/cases", json=payload, headers=ACTOR)
    assert r.status_code == 201
    return r.json()["id"]


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
    assert r.json()["total_cases"] == 0


def test_invalid_api_key():
    r = client.get("/summary", headers={"X-API-Key": "wrong"})
    assert r.status_code == 401


def test_create_and_get_case():
    case_id = _create_case()
    r2 = client.get(f"/cases/{case_id}", headers=AUTH)
    assert r2.status_code == 200
    assert r2.json()["title"] == "Test DI case"
    assert r2.json()["status"] == "intake"


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


def test_list_cases_invalid_status_query():
    r = client.get("/cases?status=not_a_real_status", headers=AUTH)
    assert r.status_code == 422


def test_list_cases_valid_status_filter():
    _create_case("Filter me")
    r = client.get("/cases?status=intake", headers=AUTH)
    assert r.status_code == 200
    assert all(c["status"] == "intake" for c in r.json())


def test_update_case_status_and_close():
    case_id = _create_case()
    r = client.patch(
        f"/cases/{case_id}/status",
        json={"status": "investigation"},
        headers=ACTOR,
    )
    assert r.status_code == 200
    assert r.json()["status"] == "investigation"

    r2 = client.post(f"/cases/{case_id}/close", headers=ACTOR)
    assert r2.status_code == 200
    assert r2.json()["status"] == "closed"
    assert r2.json()["closed_at"] is not None


def test_invalid_case_status_transition():
    case_id = _create_case()
    # intake cannot jump directly to capa_formulation
    r = client.patch(
        f"/cases/{case_id}/status",
        json={"status": "capa_formulation"},
        headers=ACTOR,
    )
    assert r.status_code == 409


def test_closed_case_blocks_mutations():
    case_id = _create_case()
    client.post(f"/cases/{case_id}/close", headers=ACTOR)
    gap = {
        "attribute": "Attributable",
        "gap_found": True,
        "observation": "Should fail",
        "assessed_by": "tester",
    }
    r = client.post(f"/cases/{case_id}/alcoa-gaps", json=gap, headers=ACTOR)
    assert r.status_code == 409


def test_alcoa_gap():
    case_id = _create_case("ALCOA test")
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
    case_id = _create_case("Ev test")
    ev = {
        "evidence_type": "audit_trail_review",
        "description": "Reviewed 30-day export",
        "recorded_by": "tester",
    }
    r = client.post(f"/cases/{case_id}/evidence", json=ev, headers=ACTOR)
    assert r.status_code == 201


def test_capa_and_status_update():
    case_id = _create_case("CAPA test")
    capa = {
        "action_type": "corrective",
        "description": "Fix the actor field in LIMS config",
        "owner": "tester",
        "due_date": "2026-12-01",
    }
    r = client.post(f"/cases/{case_id}/capas", json=capa, headers=ACTOR)
    assert r.status_code == 201
    capa_id = r.json()["id"]
    assert r.json()["status"] == "open"

    r2 = client.patch(
        f"/cases/{case_id}/capas/{capa_id}/status",
        json={"status": "in_progress"},
        headers=ACTOR,
    )
    assert r2.status_code == 200
    assert r2.json()["status"] == "in_progress"

    r3 = client.patch(
        f"/cases/{case_id}/capas/{capa_id}/status",
        json={"status": "verified"},
        headers=ACTOR,
    )
    assert r3.status_code == 200
    assert r3.json()["status"] == "verified"


def test_audit_log():
    _create_case("Audit test")
    r = client.get("/audit-log", headers=AUTH)
    assert r.status_code == 200
    assert len(r.json()) >= 1


def test_case_not_found():
    r = client.get("/cases/99999", headers=AUTH)
    assert r.status_code == 404


def test_summary_after_creates():
    for i in range(3):
        _create_case(f"Case {i}")
    r = client.get("/summary", headers=AUTH)
    assert r.json()["total_cases"] == 3


def test_rate_limit_headers_present():
    r = client.get("/summary", headers=AUTH)
    assert r.status_code == 200
    assert "X-RateLimit-Limit" in r.headers
    assert "X-RateLimit-Remaining" in r.headers
