from app import ai_status


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def test_ai_status_ready(monkeypatch):
    monkeypatch.setattr(
        ai_status.httpx,
        "get",
        lambda *_args, **_kwargs: FakeResponse({"models": [{"name": ai_status.OLLAMA_MODEL}]}),
    )

    result = ai_status.get_ai_status()

    assert result.status == "ready"
    assert result.service_available is True
    assert result.model_available is True


def test_ai_status_model_not_installed(monkeypatch):
    monkeypatch.setattr(
        ai_status.httpx,
        "get",
        lambda *_args, **_kwargs: FakeResponse({"models": [{"name": "other-model:latest"}]}),
    )

    result = ai_status.get_ai_status()

    assert result.status == "model_not_installed"
    assert result.service_available is True
    assert result.model_available is False


def test_ai_status_service_unavailable(monkeypatch):
    def unavailable(*_args, **_kwargs):
        raise ai_status.httpx.ConnectError("not reachable")

    monkeypatch.setattr(ai_status.httpx, "get", unavailable)

    result = ai_status.get_ai_status()

    assert result.status == "service_unavailable"
    assert result.service_available is False
    assert result.model_available is False
