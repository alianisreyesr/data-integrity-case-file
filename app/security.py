"""API key authentication, rate limiting, and security headers.

Designed for the portfolio prototype:
- X-API-Key required on all routes except /health (and OpenAPI docs)
- Constant-time key comparison
- Per-client sliding window rate limits (stricter on AI endpoints); X-Forwarded-For
  is honoured only when the direct peer is a configured trusted proxy
- Baseline HTTP security headers on every response
"""
from __future__ import annotations

import ipaddress
import os
import secrets
import time
from collections import deque
from collections.abc import Callable

from fastapi import Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

# ── Configuration ────────────────────────────────────────────────────────────

DEFAULT_API_KEY = "dev-api-key-change-me"
API_KEY = os.getenv("API_KEY", DEFAULT_API_KEY)
API_KEY_HEADER = "X-API-Key"
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
DEV_ENVIRONMENTS = frozenset({"dev", "development", "test", "testing", "local"})


def ensure_api_key_configured(api_key: str | None = None, environment: str | None = None) -> None:
    """Refuse to start with the public default key outside development."""
    key = API_KEY if api_key is None else api_key
    env = (ENVIRONMENT if environment is None else environment).strip().lower()
    if env not in DEV_ENVIRONMENTS and (not key or key == DEFAULT_API_KEY):
        raise RuntimeError(
            f"API_KEY must be set to a private value when ENVIRONMENT is '{env}' "
            "(the built-in default is only allowed in development)."
        )

RATE_LIMIT_DEFAULT = int(os.getenv("RATE_LIMIT_DEFAULT", "120"))
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))
RATE_LIMIT_AI = int(os.getenv("RATE_LIMIT_AI", "10"))
RATE_LIMIT_AI_WINDOW = int(os.getenv("RATE_LIMIT_AI_WINDOW_SECONDS", "60"))

PUBLIC_PATHS = frozenset({"/health", "/docs", "/openapi.json", "/redoc"})


def _parse_trusted_proxies(raw: str) -> list[ipaddress.IPv4Network | ipaddress.IPv6Network]:
    networks: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = []
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        try:
            networks.append(ipaddress.ip_network(item, strict=False))
        except ValueError:
            continue  # ignore malformed entries rather than trusting everything
    return networks


# Comma-separated IPs/CIDRs of reverse proxies allowed to set X-Forwarded-For.
# Empty (default) means the header is never trusted and the socket peer is used.
TRUSTED_PROXIES = _parse_trusted_proxies(os.getenv("TRUSTED_PROXIES", ""))


def _as_ip(value: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    try:
        return ipaddress.ip_address(value.strip())
    except ValueError:
        return None


def _is_trusted(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return any(ip in net for net in TRUSTED_PROXIES)


def _client_id(request: Request) -> str:
    peer = request.client.host if request.client and request.client.host else "unknown"
    forwarded = request.headers.get("x-forwarded-for")
    peer_ip = _as_ip(peer)
    if not forwarded or not TRUSTED_PROXIES or peer_ip is None or not _is_trusted(peer_ip):
        return peer
    # Walk the chain from the right: the first address that is not one of our
    # trusted proxies is the real client. Anything further left is client-supplied.
    for part in reversed(forwarded.split(",")):
        ip = _as_ip(part)
        if ip is None:
            return peer  # malformed chain: fall back to the proxy address
        if not _is_trusted(ip):
            return str(ip)
    return peer


class SlidingWindowLimiter:
    """In-memory sliding-window rate limiter. Suitable for single-process demo.

    Memory is bounded: expired buckets are purged periodically and the number
    of tracked keys is capped at ``max_keys`` (oldest keys are evicted first).
    """

    def __init__(self, max_keys: int = 10_000, sweep_every: int = 500) -> None:
        self._hits: dict[str, deque[float]] = {}
        self._max_keys = max_keys
        self._sweep_every = sweep_every
        self._calls = 0

    def _sweep(self, now: float, window_seconds: int) -> None:
        stale = [k for k, q in self._hits.items() if not q or q[-1] < now - window_seconds]
        for k in stale:
            del self._hits[k]

    def allow(self, key: str, limit: int, window_seconds: int) -> tuple[bool, int, int]:
        now = time.monotonic()
        self._calls += 1
        if self._calls % self._sweep_every == 0 or len(self._hits) >= self._max_keys:
            self._sweep(now, max(window_seconds, RATE_LIMIT_WINDOW, RATE_LIMIT_AI_WINDOW))
        while len(self._hits) >= self._max_keys and key not in self._hits:
            del self._hits[next(iter(self._hits))]  # evict oldest-inserted key
        window_start = now - window_seconds
        q = self._hits.setdefault(key, deque())
        while q and q[0] < window_start:
            q.popleft()
        if len(q) >= limit:
            retry_after = max(1, int(q[0] + window_seconds - now) + 1)
            return False, 0, retry_after
        q.append(now)
        remaining = max(0, limit - len(q))
        return True, remaining, 0


_limiter = SlidingWindowLimiter()


def _is_ai_path(path: str) -> bool:
    return "/ai-suggest-gaps" in path


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        if path in PUBLIC_PATHS or path.startswith(("/docs", "/redoc")):
            return await call_next(request)

        client = _client_id(request)
        if _is_ai_path(path) and request.method == "POST":
            limit, window = RATE_LIMIT_AI, RATE_LIMIT_AI_WINDOW
            bucket = f"ai:{client}"
        else:
            limit, window = RATE_LIMIT_DEFAULT, RATE_LIMIT_WINDOW
            bucket = f"default:{client}"

        allowed, remaining, retry_after = _limiter.allow(bucket, limit, window)
        if not allowed:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Rate limit exceeded. Slow down and retry.",
                    "retry_after_seconds": retry_after,
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response


class ApiKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        if (
            path in PUBLIC_PATHS
            or path.startswith(("/docs", "/redoc", "/openapi"))
        ):
            return await call_next(request)

        key = request.headers.get(API_KEY_HEADER)
        if not key or not secrets.compare_digest(key, API_KEY):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid or missing API key. Send header X-API-Key."},
                headers={"WWW-Authenticate": "ApiKey"},
            )
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Baseline browser/security headers for a local API prototype."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy",
            "camera=(), microphone=(), geolocation=()",
        )
        # API-oriented CSP: no scripts expected from this origin for JSON clients
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'none'; frame-ancestors 'none'",
        )
        response.headers.setdefault("X-Data-Boundary", "synthetic-only")
        return response
