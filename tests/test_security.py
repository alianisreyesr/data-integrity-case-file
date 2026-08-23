"""Security-focused tests: API key and rate limiting."""
import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("API_KEY", "test-api-key")

from app.main import app
from app.database import init_db_sync
import app.security as security_mod

security_mod.API_KEY = "test-api-key"
security_mod.RATE_LIMIT_DEFAULT = 5
security_mod.RATE_LIMIT_WINDOW = 60
security_mod._limiter = security_mod.SlidingWindowLimiter()

client = TestClient(app)
AUTH = {"X-API-Key": "test-api-key"}


@pytest.fixture(autouse=True)
def setup_db(tmp_path, monkeypatch):
    db = str(tmp_path / "test.db")
    monkeypatch.setenv("DB_PATH", db)
    import app.database as db_mod

    db_mod.DB_PATH = db
    init_db_sync()
    security_mod._limiter = security_mod.SlidingWindowLimiter()
    yield


def test_missing_api_key_returns_401():
    r = client.get("/cases")
    assert r.status_code == 401
    assert "API key" in r.json()["detail"]


def test_wrong_api_key_returns_401():
    r = client.get("/cases", headers={"X-API-Key": "not-the-key"})
    assert r.status_code == 401


def test_health_does_not_require_api_key():
    r = client.get("/health")
    assert r.status_code == 200


def test_rate_limit_exceeded_returns_429():
    security_mod.RATE_LIMIT_DEFAULT = 3
    security_mod._limiter = security_mod.SlidingWindowLimiter()
    for _ in range(3):
        r = client.get("/summary", headers=AUTH)
        assert r.status_code == 200
    r = client.get("/summary", headers=AUTH)
    assert r.status_code == 429
    body = r.json()
    assert "Rate limit" in body["detail"]
    assert "Retry-After" in r.headers
