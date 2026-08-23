import pytest

from app import ai


def test_valid_ai_response_parses(monkeypatch):
    monkeypatch.setattr(
        ai,
        "call_ollama_chat",
        lambda _: {
            "message": {
                "content": (
                    '{"suggestions":[{"attribute":"Attributable","risk_level":"high",'
                    '"rationale":"Shared credentials require review."}],'
                    '"limitations":"Human review is required."}'
                )
            }
        },
    )

    result = ai.generate_gap_suggestions("Shared account", "LIMS-01", "user_access_anomaly")

    assert result.suggestions[0].attribute == "Attributable"
    assert result.suggestions[0].risk_level == "high"


def test_unsupported_attribute_is_rejected(monkeypatch):
    monkeypatch.setattr(
        ai,
        "call_ollama_chat",
        lambda _: {
            "message": {
                "content": (
                    '{"suggestions":[{"attribute":"UnapprovedAttribute","risk_level":"high",'
                    '"rationale":"Invalid controlled vocabulary."}],'
                    '"limitations":"Human review is required."}'
                )
            }
        },
    )

    with pytest.raises(ai.AiUnavailableError, match="unsupported values"):
        ai.generate_gap_suggestions("Case", "LIMS-01", "audit_finding")


def test_unsupported_risk_level_is_rejected(monkeypatch):
    monkeypatch.setattr(
        ai,
        "call_ollama_chat",
        lambda _: {
            "message": {
                "content": (
                    '{"suggestions":[{"attribute":"Original","risk_level":"critical",'
                    '"rationale":"Invalid controlled vocabulary."}],'
                    '"limitations":"Human review is required."}'
                )
            }
        },
    )

    with pytest.raises(ai.AiUnavailableError, match="unsupported values"):
        ai.generate_gap_suggestions("Case", "LIMS-01", "audit_finding")


def test_malformed_json_is_rejected(monkeypatch):
    monkeypatch.setattr(ai, "call_ollama_chat", lambda _: {"message": {"content": "not-json"}})

    with pytest.raises(ai.AiUnavailableError, match="invalid JSON"):
        ai.generate_gap_suggestions("Case", "LIMS-01", "audit_finding")
