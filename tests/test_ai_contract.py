import pytest

from app import ai


@pytest.mark.asyncio
async def test_valid_ai_response_parses(monkeypatch):
    async def fake_chat(_):
        return {
            "message": {
                "content": (
                    '{"suggestions":[{"attribute":"Attributable","risk_level":"high",'
                    '"rationale":"Shared credentials require review."}],'
                    '"limitations":"Human review is required."}'
                )
            }
        }

    monkeypatch.setattr(ai, "call_ollama_chat", fake_chat)
    result = await ai.generate_gap_suggestions("Shared account", "LIMS-01", "user_access_anomaly")
    assert result.suggestions[0].attribute == "Attributable"
    assert result.suggestions[0].risk_level == "high"


@pytest.mark.asyncio
async def test_unsupported_attribute_is_rejected(monkeypatch):
    async def fake_chat(_):
        return {
            "message": {
                "content": (
                    '{"suggestions":[{"attribute":"UnapprovedAttribute","risk_level":"high",'
                    '"rationale":"Invalid controlled vocabulary."}],'
                    '"limitations":"Human review is required."}'
                )
            }
        }

    monkeypatch.setattr(ai, "call_ollama_chat", fake_chat)
    with pytest.raises(ai.AiUnavailableError, match="unsupported values"):
        await ai.generate_gap_suggestions("Case", "LIMS-01", "audit_finding")


@pytest.mark.asyncio
async def test_unsupported_risk_level_is_rejected(monkeypatch):
    async def fake_chat(_):
        return {
            "message": {
                "content": (
                    '{"suggestions":[{"attribute":"Original","risk_level":"critical",'
                    '"rationale":"Invalid controlled vocabulary."}],'
                    '"limitations":"Human review is required."}'
                )
            }
        }

    monkeypatch.setattr(ai, "call_ollama_chat", fake_chat)
    with pytest.raises(ai.AiUnavailableError, match="unsupported values"):
        await ai.generate_gap_suggestions("Case", "LIMS-01", "audit_finding")


@pytest.mark.asyncio
async def test_malformed_json_is_rejected(monkeypatch):
    async def fake_chat(_):
        return {"message": {"content": "not-json"}}

    monkeypatch.setattr(ai, "call_ollama_chat", fake_chat)
    with pytest.raises(ai.AiUnavailableError, match="invalid JSON"):
        await ai.generate_gap_suggestions("Case", "LIMS-01", "audit_finding")
