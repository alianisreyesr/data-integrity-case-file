"""API key authentication, rate limiting, and security headers.

Designed for the portfolio prototype:
- X-API-Key required on all routes except /health (and OpenAPI docs)
- Constant-time key comparison
- Per-client sliding window rate limits (stricter on AI endpoints)
- Baseline HTTP security headers on every response
"""
from __future__ import annotations

import os
import secrets
import time
from collections import defaultdict, deque
from typing import Callable, Deque, Dict, Optional

from fastapi import Header, HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

# ── Configuration ────────────────────────────────────────────────────────────

API_KEY = os.getenv("API_KEY", "dev-api-key-change-me")
API_KEY_HEADER = "X-API-Key"

RATE_LIMIT_DEFAULT = int(os.getenv("RATE_LIMIT_DEFAULT", "120"))
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))
RATE_LIMIT_AI = int(os.getenv("RATE_LIMIT_AI", "10"))
RATE_LIMIT_AI_WINDOW = int(os.getenv("RATE_LIMIT_AI_WINDOW_SECONDS", "60"))

PUBLIC_PATHS = frozenset({"/health", "/docs", "/openapi.json", "/redoc"})


def _client_id(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host or "unknown"
    return "unknown"


async def require_api_key(x_api_key: Optional[str] = Header(None, alias=API_KEY_HEADER)) -> str:
    if not x_api_key or not secrets.compare_digest(x_api_key, API_KEY):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key. Send header X-API-Key.",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    return x_api_key


class SlidingWindowLimiter:
    """In-memory sliding-window rate limiter. Suitable for single-process demo."""

    def __init__(self) -> None:
        self._hits: Dict[str, Deque[float]] = defaultdict(deque)

    def allow(self, key: str, limit: int, window_seconds: int) -> tuple[bool, int, int]:
        now = time.monotonic()
        window_start = now - window_seconds
        q = self._hits[key]
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
    return path.rstrip("/").endswith("ai-suggest-gaps") or "/ai-suggest-gaps" in path


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        if path in PUBLIC_PATHS or path.startswith("/docs") or path.startswith("/redoc"):
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
            or path.startswith("/docs")
            or path.startswith("/redoc")
            or path.startswith("/openapi")
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
