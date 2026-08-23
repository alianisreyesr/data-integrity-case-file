from __future__ import annotations
from datetime import datetime, timezone
from typing import Literal, Optional
from pydantic import BaseModel, Field


ALCOA_ATTRIBUTES = Literal[
    "Attributable", "Legible", "Contemporaneous",
    "Original", "Accurate", "Complete",
    "Consistent", "Enduring", "Available"
]

SIGNAL_TYPES = Literal[
    "audit_finding", "system_discrepancy",
    "user_access_anomaly", "data_gap", "process_deviation"
]

CASE_STATUSES = Literal[
    "intake", "alcoa_assessment", "investigation",
    "capa_formulation", "closed"
]

CAPA_TYPES = Literal["corrective", "preventive"]
CAPA_STATUSES = Literal["open", "in_progress", "verified", "closed"]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Case ──────────────────────────────────────────────────────────────────────

class CaseCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    system: str = Field(..., min_length=2, max_length=100)
    signal_type: SIGNAL_TYPES
    opened_by: str = Field(..., min_length=2, max_length=80)


class CaseOut(BaseModel):
    id: int
    case_ref: str
    title: str
    system: str
    signal_type: str
    status: str
    opened_by: str
    opened_at: str
    closed_at: Optional[str] = None


# ── ALCOA+ Gap ────────────────────────────────────────────────────────────────

class AlcoaGapCreate(BaseModel):
    attribute: ALCOA_ATTRIBUTES
    gap_found: bool
    observation: Optional[str] = Field(None, max_length=500)
    assessed_by: str = Field(..., min_length=2, max_length=80)


class AlcoaGapOut(BaseModel):
    id: int
    case_id: int
    attribute: str
    gap_found: bool
    observation: Optional[str]
    assessed_by: str
    assessed_at: str


# ── Evidence ──────────────────────────────────────────────────────────────────

class EvidenceCreate(BaseModel):
    evidence_type: Literal[
        "audit_trail_review", "technical_metadata",
        "access_log", "screenshot", "interview_note"
    ]
    description: str = Field(..., min_length=5, max_length=1000)
    recorded_by: str = Field(..., min_length=2, max_length=80)


class EvidenceOut(BaseModel):
    id: int
    case_id: int
    evidence_type: str
    description: str
    recorded_by: str
    recorded_at: str


# ── CAPA ──────────────────────────────────────────────────────────────────────

class CapaCreate(BaseModel):
    action_type: CAPA_TYPES
    description: str = Field(..., min_length=10, max_length=1000)
    owner: str = Field(..., min_length=2, max_length=80)
    due_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")


class CapaOut(BaseModel):
    id: int
    case_id: int
    capa_ref: str
    action_type: str
    description: str
    owner: str
    due_date: str
    status: str
    created_at: str


# ── Audit Log ─────────────────────────────────────────────────────────────────

class AuditEntry(BaseModel):
    id: int
    case_id: Optional[int]
    actor: str
    action: str
    detail: Optional[str]
    created_at: str


# ── Summary ───────────────────────────────────────────────────────────────────

class SummaryOut(BaseModel):
    total_cases: int
    open_cases: int
    closed_cases: int
    total_gaps_found: int
    total_capas: int
    open_capas: int
    data_boundary: str = "All records are synthetic and fictional."
