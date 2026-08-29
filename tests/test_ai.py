import os

from fastapi.testclient import TestClient

os.environ.setdefault("API_KEY", "test-api-key")

from app.main import app
import app.router as router_module
from app import ai as ai_module
import app.security as security_mod

security_mod.API_KEY = "test-api-key"

client = TestClient(app)
AUTH = {"X-API-Key": "test-api-key"}
ACTOR = {"x-actor": "tester", **AUTH}


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

    async def fake_generate(title, system_name, signal_type):
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


def test_ai_suggest_gaps_unavailable(monkeypatch):
    case_id = _create_case()

    async def fake_generate(title, system_name, signal_type):
        raise ai_module.AiUnavailableError("model not reachable")

    monkeypatch.setattr(router_module, "generate_gap_suggestions", fake_generate)

    r = client.post(f"/cases/{case_id}/ai-suggest-gaps", headers=ACTOR)
    assert r.status_code == 503


def test_review_ai_suggestion(monkeypatch):
    case_id = _create_case()

    async def fake_generate(title, system_name, signal_type):
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
    body = r.json()
    assert body["suggestion"]["human_action"] == "accepted"
    assert body["suggestion"]["integrity_verified"] is True
    # Accepting writes one alcoa_gaps row per suggested attribute.
    assert len(body["gaps_recorded"]) == 1
    assert body["gaps_recorded"][0]["attribute"] == "Original"
    assert body["gaps_recorded"][0]["gap_found"] is True

    gaps = client.get(f"/cases/{case_id}/alcoa-gaps", headers=AUTH).json()
    assert len(gaps) == 1
    assert gaps[0]["assessed_by"] == "qa_reviewer"


def test_review_ai_suggestion_is_not_repeatable(monkeypatch):
    case_id = _create_case()

    async def fake_generate(title, system_name, signal_type):
        return ai_module.AiGapResponse(
            suggestions=[
                ai_module.AiGapSuggestion(
                    attribute="Complete", risk_level="low", rationale="Check completeness."
                )
            ],
            limitations="Suggestions require qualified human review.",
        )

    monkeypatch.setattr(router_module, "generate_gap_suggestions", fake_generate)
    created = client.post(f"/cases/{case_id}/ai-suggest-gaps", headers=ACTOR).json()

    review_headers = {"x-actor": "qa_reviewer", **AUTH}
    review_body = {"human_action": "rejected", "reviewed_by": "qa_reviewer"}
    first = client.post(f"/ai-suggestions/{created['id']}/review", json=review_body, headers=review_headers)
    assert first.status_code == 200

    second = client.post(f"/ai-suggestions/{created['id']}/review", json=review_body, headers=review_headers)
    assert second.status_code == 409


def test_rejected_suggestion_does_not_write_gaps(monkeypatch):
    case_id = _create_case()

    async def fake_generate(title, system_name, signal_type):
        return ai_module.AiGapResponse(
            suggestions=[
                ai_module.AiGapSuggestion(
                    attribute="Enduring", risk_level="high", rationale="Check retention."
                )
            ],
            limitations="Suggestions require qualified human review.",
        )

    monkeypatch.setattr(router_module, "generate_gap_suggestions", fake_generate)
    created = client.post(f"/cases/{case_id}/ai-suggest-gaps", headers=ACTOR).json()

    r = client.post(
        f"/ai-suggestions/{created['id']}/review",
        json={"human_action": "rejected", "reviewed_by": "qa_reviewer"},
        headers={"x-actor": "qa_reviewer", **AUTH},
    )
    assert r.status_code == 200
    assert r.json()["gaps_recorded"] == []
    gaps = client.get(f"/cases/{case_id}/alcoa-gaps", headers=AUTH).json()
    assert gaps == []


def test_list_ai_suggestions_empty():
    case_id = _create_case()
    r = client.get(f"/cases/{case_id}/ai-suggestions", headers=AUTH)
    assert r.status_code == 200
    assert r.json() == []
