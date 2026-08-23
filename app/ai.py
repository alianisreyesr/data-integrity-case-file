"""Local, open-source LLM assistant for ALCOA+ gap triage.

This module never writes directly to case records. It produces structured
suggestions that a qualified human must explicitly accept, reject, or modify.
All requests are sent to a locally hosted Ollama instance; no case data is
sent to any third-party API.
"""
from __future__ import annotations

import hashlib
import json
import os
from typing import List, Literal

import httpx
from pydantic import BaseModel, ValidationError

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
PROMPT_VERSION = "ai-gap-triage-v1"

ALCOA_ATTRIBUTE = Literal[
    "Attributable",
    "Legible",
    "Contemporaneous",
    "Original",
    "Accurate",
    "Complete",
    "Consistent",
    "Enduring",
    "Available",
]
RISK_LEVEL = Literal["low", "medium", "high"]

SYSTEM_PROMPT = (
    "You are an assistive data-integrity triage tool for a portfolio prototype. "
    "You do not make compliance decisions and your output always requires human "
    "review before any record is changed. Given a case title, system, and signal "
    "type, suggest which ALCOA+ attributes (Attributable, Legible, Contemporaneous, "
    "Original, Accurate, Complete, Consistent, Enduring, Available) most likely need "
    "investigation. Reply with JSON only, in this exact shape: "
    '{"suggestions": [{"attribute": "...", "risk_level": "low|medium|high", '
    '"rationale": "..."}], "limitations": "..."}'
)


class AiGapSuggestion(BaseModel):
    attribute: ALCOA_ATTRIBUTE
    risk_level: RISK_LEVEL
    rationale: str


class AiGapResponse(BaseModel):
    suggestions: List[AiGapSuggestion]
    limitations: str


class AiUnavailableError(Exception):
    """Raised when the local model cannot be reached or returns invalid output."""


def call_ollama_chat(user_prompt: str) -> dict:
    payload = {
        "model": OLLAMA_MODEL,
        "stream": False,
        "format": "json",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    }
    try:
        response = httpx.post(f"{OLLAMA_BASE_URL}/api/chat", json=payload, timeout=60)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise AiUnavailableError(f"Ollama request failed: {exc}") from exc
    return response.json()


def generate_gap_suggestions(title: str, system_name: str, signal_type: str) -> AiGapResponse:
    user_prompt = (
        f"Case title: {title}\nSystem: {system_name}\nSignal type: {signal_type}\n"
        "Return JSON only."
    )
    raw = call_ollama_chat(user_prompt)
    content = raw.get("message", {}).get("content", "")
    try:
        parsed = json.loads(content)
        return AiGapResponse(**parsed)
    except (json.JSONDecodeError, ValidationError) as exc:
        raise AiUnavailableError(f"Model returned invalid JSON or unsupported values: {exc}") from exc


def hash_response(payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
