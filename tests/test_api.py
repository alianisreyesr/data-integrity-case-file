import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import init_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db(tmp_path, monkeypatch):
    db = str(tmp_path / "test.db")
    monkeypatch.setenv("DB_PATH", db)
    import app.database as db_mod
    db_mod.DB_PATH = db
    init_db()
    yield


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_summary_empty():
    r = client.get("/summary")
    assert r.status_code == 200
    data = r.json()
    assert data["total_cases"] == 0


def test_create_and_get_case():
    payload = {"title": "Test DI case", "system": "LIMS-01",
               "signal_type": "audit_finding", "opened_by": "tester"}
    r = client.post("/cases", json=payload, headers={"x-actor": "tester"})
    assert r.status_code == 201
    case_id = r.json()["id"]
    r2 = client.get(f"/cases/{case_id}")
    assert r2.status_code == 200
    assert r2.json()["title"] == "Test DI case"


def test_create_case_missing_actor():
    payload = {"title": "No actor", "system": "SYS",
               "signal_type": "data_gap", "opened_by": "tester"}
    r = client.post("/cases", json=payload)
    assert r.status_code == 422


def test_alcoa_gap():
    payload = {"title": "ALCOA test", "system": "SYS",
               "signal_type": "audit_finding", "opened_by": "tester"}
    case_id = client.post("/cases", json=payload, headers={"x-actor": "tester"}).json()["id"]
    gap = {"attribute": "Attributable", "gap_found": True,
           "observation": "Actor field blank", "assessed_by": "tester"}
    r = client.post(f"/cases/{case_id}/alcoa-gaps", json=gap, headers={"x-actor": "tester"})
    assert r.status_code == 201
    assert r.json()["gap_found"] == True


def test_evidence():
    case_id = client.post("/cases",
        json={"title": "Ev test", "system": "SYS",
              "signal_type": "data_gap", "opened_by": "tester"},
        headers={"x-actor": "tester"}).json()["id"]
    ev = {"evidence_type": "audit_trail_review",
          "description": "Reviewed 30-day export", "recorded_by": "tester"}
    r = client.post(f"/cases/{case_id}/evidence", json=ev, headers={"x-actor": "tester"})
    assert r.status_code == 201


def test_capa():
    case_id = client.post("/cases",
        json={"title": "CAPA test", "system": "SYS",
              "signal_type": "data_gap", "opened_by": "tester"},
        headers={"x-actor": "tester"}).json()["id"]
    capa = {"action_type": "corrective", "description": "Fix the actor field in LIMS config",
            "owner": "tester", "due_date": "2026-12-01"}
    r = client.post(f"/cases/{case_id}/capas", json=capa, headers={"x-actor": "tester"})
    assert r.status_code == 201
    assert r.json()["status"] == "open"


def test_audit_log():
    client.post("/cases",
        json={"title": "Audit test", "system": "SYS",
              "signal_type": "audit_finding", "opened_by": "tester"},
        headers={"x-actor": "tester"})
    r = client.get("/audit-log")
    assert r.status_code == 200
    assert len(r.json()) >= 1


def test_case_not_found():
    r = client.get("/cases/99999")
    assert r.status_code == 404


def test_summary_after_creates():
    for i in range(3):
        client.post("/cases",
            json={"title": f"Case {i}", "system": "SYS",
                  "signal_type": "audit_finding", "opened_by": "tester"},
            headers={"x-actor": "tester"})
    r = client.get("/summary")
    assert r.json()["total_cases"] == 3
