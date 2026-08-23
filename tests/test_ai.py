import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("API_KEY", "test-api-key")

from app.main import app
from app.database import init_db
import app.router as router_module
from app import ai as ai_module
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


def _create_case():
    payload = {
        "title": "Shared login credential detected",
        "system": "LIMS-01",
        "signal_type": "user_access_anomaly",
        "opened_by": "tester",
    }
    r = client.post("/cases", json=payload, headers=ACTOR)
    return r.json()["id"]


def test_ai_suggest_gaps_success(monkeypatch):
    case_id = _create_case()

    def fake_generate(title, system_name, signal_type):
        return ai_module.AiGapResponse(
            suggestions=[
                ai_module.AiGapSuggestion(
                    attribute="Attributable",
                    risk_level="high",
                    rationale="Shared credentials break attributable action.",
                )
            ],
            limitations="Suggestions require qualified human review.",
        )

    monkeypatch.setattr(router_module, "generate_gap_suggestions", fake_generate)

    r = client.post(f"/cases/{case_id}/ai-suggest-gaps", headers=ACTOR)
    assert r.status_code == 201
    body = r.json()
    assert body["model_provider"] == "local_ollama"
    assert body["suggestions"][0]["attribute"] == "Attributable"
    assert body["human_action"] is None


def test_ai_suggest_gaps_unavailable(monkeypatch):
    case_id = _create_case()

    def fake_generate(title, system_name, signal_type):
        raise ai_module.AiUnavailableError("model not reachable")

    monkeypatch.setattr(router_module, "generate_gap_suggestions", fake_generate)

    r = client.post(f"/cases/{case_id}/ai-suggest-gaps", headers=ACTOR)
    assert r.status_code == 503


def test_review_ai_suggestion(monkeypatch):
    case_id = _create_case()

    def fake_generate(title, system_name, signal_type):
        return ai_module.AiGapResponse(
            suggestions=[
                ai_module.AiGapSuggestion(
                    attribute="Original", risk_level="medium", rationale="Check source preservation."
                )
            ],
            limitations="Suggestions require qualified human review.",
        )

    monkeypatch.setattr(router_module, "generate_gap_suggestions", fake_generate)
    created = client.post(f"/cases/{case_id}/ai-suggest-gaps", headers=ACTOR).json()

    r = client.post(
        f"/ai-suggestions/{created['id']}/review",
        json={"human_action": "accepted", "reviewed_by": "qa_reviewer"},
        headers={"x-actor": "qa_reviewer", **AUTH},
    )
    assert r.status_code == 200
    assert r.json()["human_action"] == "accepted"
    assert r.json()["reviewed_by"] == "qa_reviewer"


def test_list_ai_suggestions_empty():
    case_id = _create_case()
    r = client.get(f"/cases/{case_id}/ai-suggestions", headers=AUTH)
    assert r.status_code == 200
    assert r.json() == []
