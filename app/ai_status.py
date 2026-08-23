"""Read-only readiness checks for the local Ollama service."""
from __future__ import annotations

import os
from typing import Literal

import httpx
from fastapi import APIRouter
from pydantic import BaseModel

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")

router = APIRouter()


class AiStatusOut(BaseModel):
    status: Literal["ready", "model_not_installed", "service_unavailable"]
    configured_model: str
    service_available: bool
    model_available: bool
    message: str


def get_ai_status() -> AiStatusOut:
    try:
        response = httpx.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=3)
        response.raise_for_status()
        models = response.json().get("models", [])
    except (httpx.HTTPError, ValueError):
        return AiStatusOut(
            status="service_unavailable",
            configured_model=OLLAMA_MODEL,
            service_available=False,
            model_available=False,
            message="Local Ollama service is unavailable. AI-assisted triage is disabled.",
        )

    available_names = {item.get("name") or item.get("model") for item in models}
    if OLLAMA_MODEL not in available_names:
        return AiStatusOut(
            status="model_not_installed",
            configured_model=OLLAMA_MODEL,
            service_available=True,
            model_available=False,
            message=f"Ollama is running, but model {OLLAMA_MODEL} is not installed.",
        )

    return AiStatusOut(
        status="ready",
        configured_model=OLLAMA_MODEL,
        service_available=True,
        model_available=True,
        message=f"Local AI is ready with model {OLLAMA_MODEL}.",
    )


@router.get("/ai/status", response_model=AiStatusOut)
def ai_status() -> AiStatusOut:
    return get_ai_status()
