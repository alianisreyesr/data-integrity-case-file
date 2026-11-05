import asyncio

import pytest
from fastapi.testclient import TestClient

import app.database as db_mod
from app.main import app
from app.security import DEFAULT_API_KEY, ensure_api_key_configured

client = TestClient(app)
AUTH = {"X-API-Key": "test-api-key"}


def _case():
    r = client.post(
        "/cases",
        json={"title": "Hardening case", "system": "LIMS-01", "signal_type": "audit_finding", "opened_by": "tester"},
        headers={"x-actor": "tester", **AUTH},
    )
    assert r.status_code == 201
    return r.json()["id"]


@pytest.mark.parametrize("actor", ["x", "   ", "a" * 81])
def test_invalid_x_actor_rejected(actor):
    r = client.post(
        "/cases",
        json={"title": "Bad actor case", "system": "LIMS-01", "signal_type": "audit_finding", "opened_by": "tester"},
        headers={"x-actor": actor, **AUTH},
    )
    assert r.status_code == 422
    assert client.get("/audit-log", headers=AUTH).json() == []


def test_x_actor_is_trimmed_in_audit_log():
    r = client.post(
        "/cases",
        json={"title": "Trim actor case", "system": "LIMS-01", "signal_type": "audit_finding", "opened_by": "tester"},
        headers={"x-actor": "  A.Reyes  ", **AUTH},
    )
    assert r.status_code == 201
    assert client.get("/audit-log", headers=AUTH).json()[0]["actor"] == "A.Reyes"


def test_default_api_key_rejected_outside_development():
    with pytest.raises(RuntimeError):
        ensure_api_key_configured(DEFAULT_API_KEY, "production")
    with pytest.raises(RuntimeError):
        ensure_api_key_configured("", "production")
    ensure_api_key_configured("a-private-key", "production")
    ensure_api_key_configured(DEFAULT_API_KEY, "development")


def test_failed_request_is_rolled_back():
    """An exception after an uncommitted write must not leak into the next commit."""

    async def scenario():
        await db_mod.connect()
        gen = db_mod.get_db()
        db = await gen.__anext__()
        await db.execute(
            "INSERT INTO cases (case_ref,title,system,signal_type,status,opened_by,opened_at) "
            "VALUES ('DI-LEAK','t','s','audit_finding','intake','u','now')"
        )
        with pytest.raises(RuntimeError):
            await gen.athrow(RuntimeError("handler failed"))
        # A later request commits; the failed write must not be persisted by it.
        await db.commit()
        async with db.execute("SELECT COUNT(*) FROM cases WHERE case_ref='DI-LEAK'") as cur:
            count = (await cur.fetchone())[0]
        await db_mod.disconnect()
        return count

    assert asyncio.run(scenario()) == 0


def test_inserted_ids_match_created_rows():
    case_id = _case()
    ids = []
    for desc in ("first evidence item", "second evidence item"):
        r = client.post(
            f"/cases/{case_id}/evidence",
            json={"evidence_type": "access_log", "description": desc, "recorded_by": "tester"},
            headers={"x-actor": "tester", **AUTH},
        )
        assert r.status_code == 201, r.text
        assert r.json()["description"] == desc
        ids.append(r.json()["id"])
    assert len(set(ids)) == 2
