from __future__ import annotations
import json
import string, random
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Header, Query
from .database import get_connection
from .models import (
    CaseCreate, CaseOut, CaseStatusUpdate,
    AlcoaGapCreate, AlcoaGapOut,
    EvidenceCreate, EvidenceOut,
    CapaCreate, CapaOut, CapaStatusUpdate,
    AuditEntry, SummaryOut,
    AiSuggestionOut, AiSuggestionReviewCreate,
    CASE_STATUSES, CASE_STATUS_TRANSITIONS, CAPA_STATUS_TRANSITIONS,
)
from .ai import generate_gap_suggestions, hash_response, AiUnavailableError, OLLAMA_MODEL, PROMPT_VERSION

router = APIRouter()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ref(prefix: str, n: int = 6) -> str:
    return prefix + "-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=n))


def _audit(conn, actor: str, action: str, case_id: Optional[int] = None, detail: Optional[str] = None):
    conn.execute(
        "INSERT INTO audit_log (case_id, actor, action, detail, created_at) VALUES (?,?,?,?,?)",
        (case_id, actor, action, detail, _now())
    )


def _require_case(conn, case_id: int):
    row = conn.execute("SELECT * FROM cases WHERE id=?", (case_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Case not found")
    return row


def _require_open_case(conn, case_id: int):
    row = _require_case(conn, case_id)
    if row["status"] == "closed":
        raise HTTPException(409, "Case is closed; reopen is not supported in this prototype")
    return row


# ── Health ────────────────────────────────────────────────────────────────────

@router.get("/health")
def health():
    return {
        "status": "ok",
        "service": "Data Integrity Case File",
        "data_boundary": "All records are synthetic and fictional."
    }


# ── Summary ───────────────────────────────────────────────────────────────────

@router.get("/summary", response_model=SummaryOut)
def summary():
    conn = get_connection()
    r = conn.execute("SELECT COUNT(*) FROM cases").fetchone()[0]
    o = conn.execute("SELECT COUNT(*) FROM cases WHERE status != 'closed'").fetchone()[0]
    c = conn.execute("SELECT COUNT(*) FROM cases WHERE status = 'closed'").fetchone()[0]
    g = conn.execute("SELECT COUNT(*) FROM alcoa_gaps WHERE gap_found = 1").fetchone()[0]
    tc = conn.execute("SELECT COUNT(*) FROM capas").fetchone()[0]
    oc = conn.execute("SELECT COUNT(*) FROM capas WHERE status = 'open'").fetchone()[0]
    conn.close()
    return SummaryOut(total_cases=r, open_cases=o, closed_cases=c,
                      total_gaps_found=g, total_capas=tc, open_capas=oc)


# ── Cases ─────────────────────────────────────────────────────────────────────

@router.get("/cases", response_model=List[CaseOut])
def list_cases(status: Optional[CASE_STATUSES] = Query(None)):
    conn = get_connection()
    if status:
        rows = conn.execute("SELECT * FROM cases WHERE status=? ORDER BY id DESC", (status,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM cases ORDER BY id DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.post("/cases", response_model=CaseOut, status_code=201)
def create_case(body: CaseCreate, x_actor: str = Header(...)):
    conn = get_connection()
    ref = _ref("DI")
    now = _now()
    with conn:
        conn.execute(
            "INSERT INTO cases (case_ref,title,system,signal_type,status,opened_by,opened_at) VALUES (?,?,?,?,?,?,?)",
            (ref, body.title, body.system, body.signal_type, "intake", body.opened_by, now)
        )
        case_id = conn.execute("SELECT id FROM cases WHERE case_ref=?", (ref,)).fetchone()[0]
        _audit(conn, x_actor, "case_created", case_id, f"ref={ref}")
    row = conn.execute("SELECT * FROM cases WHERE id=?", (case_id,)).fetchone()
    conn.close()
    return dict(row)


@router.get("/cases/{case_id}", response_model=CaseOut)
def get_case(case_id: int):
    conn = get_connection()
    row = conn.execute("SELECT * FROM cases WHERE id=?", (case_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(404, "Case not found")
    return dict(row)


@router.patch("/cases/{case_id}/status", response_model=CaseOut)
def update_case_status(case_id: int, body: CaseStatusUpdate, x_actor: str = Header(...)):
    conn = get_connection()
    try:
        row = _require_case(conn, case_id)
        current = row["status"]
        target = body.status
        if current == target:
            return dict(row)
        allowed = CASE_STATUS_TRANSITIONS.get(current, set())
        if target not in allowed:
            raise HTTPException(
                409,
                f"Invalid transition from '{current}' to '{target}'. Allowed: {sorted(allowed) or 'none (terminal)'}",
            )
        now = _now()
        closed_at = now if target == "closed" else None
        with conn:
            if target == "closed":
                conn.execute(
                    "UPDATE cases SET status=?, closed_at=? WHERE id=?",
                    (target, closed_at, case_id),
                )
            else:
                conn.execute(
                    "UPDATE cases SET status=?, closed_at=NULL WHERE id=?",
                    (target, case_id),
                )
            _audit(conn, x_actor, "case_status_updated", case_id, f"{current}->{target}")
        updated = conn.execute("SELECT * FROM cases WHERE id=?", (case_id,)).fetchone()
        return dict(updated)
    finally:
        conn.close()


@router.post("/cases/{case_id}/close", response_model=CaseOut)
def close_case(case_id: int, x_actor: str = Header(...)):
    """Formal QA closure — sets status=closed and closed_at."""
    return update_case_status(case_id, CaseStatusUpdate(status="closed"), x_actor)


# ── ALCOA+ Gaps ───────────────────────────────────────────────────────────────

@router.get("/cases/{case_id}/alcoa-gaps", response_model=List[AlcoaGapOut])
def list_gaps(case_id: int):
    conn = get_connection()
    _require_case(conn, case_id)
    rows = conn.execute("SELECT * FROM alcoa_gaps WHERE case_id=? ORDER BY id", (case_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.post("/cases/{case_id}/alcoa-gaps", response_model=AlcoaGapOut, status_code=201)
def add_gap(case_id: int, body: AlcoaGapCreate, x_actor: str = Header(...)):
    conn = get_connection()
    _require_open_case(conn, case_id)
    now = _now()
    with conn:
        conn.execute(
            "INSERT INTO alcoa_gaps (case_id,attribute,gap_found,observation,assessed_by,assessed_at) VALUES (?,?,?,?,?,?)",
            (case_id, body.attribute, int(body.gap_found), body.observation, body.assessed_by, now)
        )
        gap_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        _audit(conn, x_actor, "alcoa_gap_recorded", case_id, f"attribute={body.attribute} gap={body.gap_found}")
    row = conn.execute("SELECT * FROM alcoa_gaps WHERE id=?", (gap_id,)).fetchone()
    conn.close()
    return dict(row)


# ── Evidence ──────────────────────────────────────────────────────────────────

@router.get("/cases/{case_id}/evidence", response_model=List[EvidenceOut])
def list_evidence(case_id: int):
    conn = get_connection()
    _require_case(conn, case_id)
    rows = conn.execute("SELECT * FROM evidence_log WHERE case_id=? ORDER BY id", (case_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.post("/cases/{case_id}/evidence", response_model=EvidenceOut, status_code=201)
def add_evidence(case_id: int, body: EvidenceCreate, x_actor: str = Header(...)):
    conn = get_connection()
    _require_open_case(conn, case_id)
    now = _now()
    with conn:
        conn.execute(
            "INSERT INTO evidence_log (case_id,evidence_type,description,recorded_by,recorded_at) VALUES (?,?,?,?,?)",
            (case_id, body.evidence_type, body.description, body.recorded_by, now)
        )
        eid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        _audit(conn, x_actor, "evidence_recorded", case_id, f"type={body.evidence_type}")
    row = conn.execute("SELECT * FROM evidence_log WHERE id=?", (eid,)).fetchone()
    conn.close()
    return dict(row)


# ── CAPA ──────────────────────────────────────────────────────────────────────

@router.get("/cases/{case_id}/capas", response_model=List[CapaOut])
def list_capas(case_id: int):
    conn = get_connection()
    _require_case(conn, case_id)
    rows = conn.execute("SELECT * FROM capas WHERE case_id=? ORDER BY id", (case_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.post("/cases/{case_id}/capas", response_model=CapaOut, status_code=201)
def add_capa(case_id: int, body: CapaCreate, x_actor: str = Header(...)):
    conn = get_connection()
    _require_open_case(conn, case_id)
    ref = _ref("CAPA")
    now = _now()
    with conn:
        conn.execute(
            "INSERT INTO capas (case_id,capa_ref,action_type,description,owner,due_date,status,created_at) VALUES (?,?,?,?,?,?,?,?)",
            (case_id, ref, body.action_type, body.description, body.owner, body.due_date, "open", now)
        )
        cid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        _audit(conn, x_actor, "capa_created", case_id, f"ref={ref} type={body.action_type}")
    row = conn.execute("SELECT * FROM capas WHERE id=?", (cid,)).fetchone()
    conn.close()
    return dict(row)


@router.patch("/cases/{case_id}/capas/{capa_id}/status", response_model=CapaOut)
def update_capa_status(case_id: int, capa_id: int, body: CapaStatusUpdate, x_actor: str = Header(...)):
    conn = get_connection()
    try:
        _require_open_case(conn, case_id)
        row = conn.execute(
            "SELECT * FROM capas WHERE id=? AND case_id=?", (capa_id, case_id)
        ).fetchone()
        if not row:
            raise HTTPException(404, "CAPA not found for this case")
        current = row["status"]
        target = body.status
        if current == target:
            return dict(row)
        allowed = CAPA_STATUS_TRANSITIONS.get(current, set())
        if target not in allowed:
            raise HTTPException(
                409,
                f"Invalid CAPA transition from '{current}' to '{target}'. Allowed: {sorted(allowed) or 'none'}",
            )
        with conn:
            conn.execute("UPDATE capas SET status=? WHERE id=?", (target, capa_id))
            _audit(conn, x_actor, "capa_status_updated", case_id, f"capa={row['capa_ref']} {current}->{target}")
        updated = conn.execute("SELECT * FROM capas WHERE id=?", (capa_id,)).fetchone()
        return dict(updated)
    finally:
        conn.close()


# ── Audit Log ─────────────────────────────────────────────────────────────────

@router.get("/audit-log", response_model=List[AuditEntry])
def audit_log(case_id: Optional[int] = None):
    conn = get_connection()
    if case_id:
        rows = conn.execute("SELECT * FROM audit_log WHERE case_id=? ORDER BY id DESC", (case_id,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM audit_log ORDER BY id DESC LIMIT 200").fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── AI-assisted ALCOA+ gap triage (assistive only) ────────────────────────────

def _serialize_ai_suggestion(row) -> dict:
    payload = json.loads(row["response_json"])
    return {
        "id": row["id"],
        "case_id": row["case_id"],
        "model_name": row["model_name"],
        "model_provider": row["model_provider"],
        "prompt_version": row["prompt_version"],
        "suggestions": payload.get("suggestions", []),
        "limitations": payload.get("limitations", ""),
        "generated_at": row["generated_at"],
        "human_action": row["human_action"],
        "reviewed_by": row["reviewed_by"],
        "reviewed_at": row["reviewed_at"],
    }


@router.post("/cases/{case_id}/ai-suggest-gaps", response_model=AiSuggestionOut, status_code=201)
def ai_suggest_gaps(case_id: int, x_actor: str = Header(...)):
    conn = get_connection()
    try:
        case_row = _require_open_case(conn, case_id)
        try:
            result = generate_gap_suggestions(case_row["title"], case_row["system"], case_row["signal_type"])
        except AiUnavailableError as exc:
            raise HTTPException(status_code=503, detail=f"AI assistant unavailable: {exc}")
        payload = result.model_dump()
        response_hash = hash_response(payload)
        now = _now()
        with conn:
            conn.execute(
                """
                INSERT INTO ai_suggestions
                (case_id, model_name, model_provider, prompt_version, response_json, response_hash, generated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (case_id, OLLAMA_MODEL, "local_ollama", PROMPT_VERSION, json.dumps(payload), response_hash, now),
            )
            suggestion_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            _audit(conn, x_actor, "ai_suggestion_generated", case_id, f"model={OLLAMA_MODEL} hash={response_hash[:12]}")
        row = conn.execute("SELECT * FROM ai_suggestions WHERE id=?", (suggestion_id,)).fetchone()
        return _serialize_ai_suggestion(row)
    finally:
        conn.close()


@router.get("/cases/{case_id}/ai-suggestions", response_model=List[AiSuggestionOut])
def list_ai_suggestions(case_id: int):
    conn = get_connection()
    try:
        _require_case(conn, case_id)
        rows = conn.execute("SELECT * FROM ai_suggestions WHERE case_id=? ORDER BY id DESC", (case_id,)).fetchall()
        return [_serialize_ai_suggestion(r) for r in rows]
    finally:
        conn.close()


@router.post("/ai-suggestions/{suggestion_id}/review", response_model=AiSuggestionOut)
def review_ai_suggestion(suggestion_id: int, body: AiSuggestionReviewCreate, x_actor: str = Header(...)):
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM ai_suggestions WHERE id=?", (suggestion_id,)).fetchone()
        if not row:
            raise HTTPException(404, "AI suggestion not found")
        _require_open_case(conn, row["case_id"])
        now = _now()
        with conn:
            conn.execute(
                "UPDATE ai_suggestions SET human_action=?, reviewed_by=?, reviewed_at=? WHERE id=?",
                (body.human_action, body.reviewed_by, now, suggestion_id),
            )
            _audit(conn, x_actor, "ai_suggestion_reviewed", row["case_id"], f"action={body.human_action}")
        updated = conn.execute("SELECT * FROM ai_suggestions WHERE id=?", (suggestion_id,)).fetchone()
        return _serialize_ai_suggestion(updated)
    finally:
        conn.close()
