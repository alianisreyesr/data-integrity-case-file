"""Security-focused tests: API key and rate limiting."""
import os

from fastapi.testclient import TestClient

os.environ.setdefault("API_KEY", "test-api-key")

import app.security as security_mod
from app.main import app

client = TestClient(app)
AUTH = {"X-API-Key": "test-api-key"}


def test_missing_api_key_returns_401():
    r = client.get("/cases")
    assert r.status_code == 401


def test_wrong_api_key_returns_401():
    r = client.get("/cases", headers={"X-API-Key": "not-the-key"})
    assert r.status_code == 401


def test_health_does_not_require_api_key():
    r = client.get("/health")
    assert r.status_code == 200


def test_rate_limit_exceeded_returns_429():
    security_mod.RATE_LIMIT_DEFAULT = 3
    security_mod.RATE_LIMIT_WINDOW = 60
    security_mod._limiter = security_mod.SlidingWindowLimiter()
    for _ in range(3):
        r = client.get("/summary", headers=AUTH)
        assert r.status_code == 200
    r = client.get("/summary", headers=AUTH)
    assert r.status_code == 429
    assert "Retry-After" in r.headers


# ── Client identification / X-Forwarded-For handling ─────────────────────────


class _FakeRequest:
    def __init__(self, peer, xff=None):
        from types import SimpleNamespace

        self.client = SimpleNamespace(host=peer) if peer else None
        self.headers = {"x-forwarded-for": xff} if xff else {}


def test_xff_ignored_without_trusted_proxies(monkeypatch):
    monkeypatch.setattr(security_mod, "TRUSTED_PROXIES", [])
    req = _FakeRequest("203.0.113.9", "1.2.3.4")
    assert security_mod._client_id(req) == "203.0.113.9"


def test_xff_ignored_when_peer_not_trusted(monkeypatch):
    monkeypatch.setattr(security_mod, "TRUSTED_PROXIES", security_mod._parse_trusted_proxies("10.0.0.0/8"))
    req = _FakeRequest("203.0.113.9", "1.2.3.4")
    assert security_mod._client_id(req) == "203.0.113.9"


def test_xff_used_when_peer_is_trusted_proxy(monkeypatch):
    monkeypatch.setattr(security_mod, "TRUSTED_PROXIES", security_mod._parse_trusted_proxies("10.0.0.0/8"))
    # The left-most entry is client-supplied; the right-most untrusted hop wins.
    req = _FakeRequest("10.0.0.5", "6.6.6.6, 198.51.100.7, 10.0.0.4")
    assert security_mod._client_id(req) == "198.51.100.7"


def test_malformed_xff_falls_back_to_peer(monkeypatch):
    monkeypatch.setattr(security_mod, "TRUSTED_PROXIES", security_mod._parse_trusted_proxies("10.0.0.0/8"))
    req = _FakeRequest("10.0.0.5", "not-an-ip")
    assert security_mod._client_id(req) == "10.0.0.5"


def test_spoofed_xff_does_not_bypass_rate_limit():
    security_mod.RATE_LIMIT_DEFAULT = 2
    security_mod._limiter = security_mod.SlidingWindowLimiter()
    codes = [
        client.get("/summary", headers={**AUTH, "X-Forwarded-For": f"9.9.9.{i}"}).status_code
        for i in range(4)
    ]
    assert codes == [200, 200, 429, 429]


def test_limiter_memory_is_bounded():
    lim = security_mod.SlidingWindowLimiter(max_keys=50, sweep_every=10)
    for i in range(500):
        lim.allow(f"k{i}", 5, 60)
    assert len(lim._hits) <= 50


def test_limiter_sweeps_expired_keys(monkeypatch):
    lim = security_mod.SlidingWindowLimiter(max_keys=1000, sweep_every=1)
    t = [1000.0]
    monkeypatch.setattr(security_mod.time, "monotonic", lambda: t[0])
    lim.allow("a", 5, 1)
    t[0] += 1000
    lim.allow("b", 5, 1)
    assert "a" not in lim._hits
