"""API key authentication and in-memory rate limiting.

Designed for the portfolio prototype:
- X-API-Key required on all routes except /health
- Constant-time key comparison
- Per-client sliding window rate limits (stricter on AI endpoints)
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

# requests per window (seconds)
RATE_LIMIT_DEFAULT = int(os.getenv("RATE_LIMIT_DEFAULT", "120"))
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))
RATE_LIMIT_AI = int(os.getenv("RATE_LIMIT_AI", "10"))
RATE_LIMIT_AI_WINDOW = int(os.getenv("RATE_LIMIT_AI_WINDOW_SECONDS", "60"))

# Paths that skip API key (readiness probes only)
PUBLIC_PATHS = frozenset({"/health", "/docs", "/openapi.json", "/redoc"})


def _client_id(request: Request) -> str:
    """Prefer X-Forwarded-For first hop, else direct client host."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host or "unknown"
    return "unknown"


# ── API Key dependency ───────────────────────────────────────────────────────

async def require_api_key(x_api_key: Optional[str] = Header(None, alias=API_KEY_HEADER)) -> str:
    """FastAPI dependency: reject requests without a valid API key."""
    if not x_api_key or not secrets.compare_digest(x_api_key, API_KEY):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key. Send header X-API-Key.",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    return x_api_key


# ── Rate limiter (sliding window, process-local) ─────────────────────────────

class SlidingWindowLimiter:
    """In-memory sliding-window rate limiter. Suitable for single-process demo."""

    def __init__(self) -> None:
        self._hits: Dict[str, Deque[float]] = defaultdict(deque)

    def allow(self, key: str, limit: int, window_seconds: int) -> tuple[bool, int, int]:
        """
        Returns (allowed, remaining, retry_after_seconds).
        """
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
    """Enforce X-API-Key on non-public paths (covers all routers uniformly)."""

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
