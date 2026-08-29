from __future__ import annotations

import json
import random
import string
from datetime import datetime, timezone
from typing import List, Optional

import aiosqlite
from fastapi import APIRouter, Depends, Header, HTTPException, Query

from .ai import (
    AiUnavailableError,
    OLLAMA_MODEL,
    PROMPT_VERSION,
    generate_gap_suggestions,
    hash_response,
)
from .database import get_db
from .models import (
    CASE_STATUS_TRANSITIONS,
    CASE_STATUSES,
    CAPA_STATUS_TRANSITIONS,
    AiSuggestionOut,
    AiSuggestionReviewCreate,
    AiSuggestionReviewResult,
    AlcoaGapCreate,
    AlcoaGapOut,
    AuditEntry,
    CapaCreate,
    CapaOut,
    CapaStatusUpdate,
    CaseCreate,
    CaseOut,
    CaseStatusUpdate,
    EvidenceCreate,
    EvidenceOut,
    SummaryOut,
)

router = APIRouter()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ref(prefix: str, n: int = 6) -> str:
    return prefix + "-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=n))


async def _audit(
    db: aiosqlite.Connection,
    actor: str,
    action: str,
    case_id: Optional[int] = None,
    detail: Optional[str] = None,
) -> None:
    await db.execute(
        "INSERT INTO audit_log (case_id, actor, action, detail, created_at) VALUES (?,?,?,?,?)",
        (case_id, actor, action, detail, _now()),
    )


async def _require_case(db: aiosqlite.Connection, case_id: int) -> aiosqlite.Row:
    async with db.execute("SELECT * FROM cases WHERE id=?", (case_id,)) as cur:
        row = await cur.fetchone()
    if not row:
        raise HTTPException(404, "Case not found")
    return row


async def _require_open_case(db: aiosqlite.Connection, case_id: int) -> aiosqlite.Row:
    row = await _require_case(db, case_id)
    if row["status"] == "closed":
        raise HTTPException(409, "Case is closed; reopen is not supported in this prototype")
    return row


@router.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "Data Integrity Case File",
        "data_boundary": "All records are synthetic and fictional.",
        "async": True,
        "db": "shared-aiosqlite",
    }


@router.get("/summary", response_model=SummaryOut)
async def summary(db: aiosqlite.Connection = Depends(get_db)):
    async with db.execute("SELECT COUNT(*) FROM cases") as c:
        total = (await c.fetchone())[0]
    async with db.execute("SELECT COUNT(*) FROM cases WHERE status != 'closed'") as c:
        open_c = (await c.fetchone())[0]
    async with db.execute("SELECT COUNT(*) FROM cases WHERE status = 'closed'") as c:
        closed = (await c.fetchone())[0]
    async with db.execute("SELECT COUNT(*) FROM alcoa_gaps WHERE gap_found = 1") as c:
        gaps = (await c.fetchone())[0]
    async with db.execute("SELECT COUNT(*) FROM capas") as c:
        capas = (await c.fetchone())[0]
    async with db.execute("SELECT COUNT(*) FROM capas WHERE status = 'open'") as c:
        open_capas = (await c.fetchone())[0]
    return SummaryOut(
        total_cases=total,
        open_cases=open_c,
        closed_cases=closed,
        total_gaps_found=gaps,
        total_capas=capas,
        open_capas=open_capas,
    )


@router.get("/cases", response_model=List[CaseOut])
async def list_cases(
    status: Optional[CASE_STATUSES] = Query(None),
    db: aiosqlite.Connection = Depends(get_db),
):
    if status:
        async with db.execute(
            "SELECT * FROM cases WHERE status=? ORDER BY id DESC", (status,)
        ) as cur:
            rows = await cur.fetchall()
    else:
        async with db.execute("SELECT * FROM cases ORDER BY id DESC") as cur:
            rows = await cur.fetchall()
    return [dict(r) for r in rows]


@router.post("/cases", response_model=CaseOut, status_code=201)
async def create_case(
    body: CaseCreate,
    x_actor: str = Header(...),
    db: aiosqlite.Connection = Depends(get_db),
):
    ref = _ref("DI")
    now = _now()
    await db.execute(
        "INSERT INTO cases (case_ref,title,system,signal_type,status,opened_by,opened_at) VALUES (?,?,?,?,?,?,?)",
        (ref, body.title, body.system, body.signal_type, "intake", body.opened_by, now),
    )
    async with db.execute("SELECT id FROM cases WHERE case_ref=?", (ref,)) as cur:
        case_id = (await cur.fetchone())[0]
    await _audit(db, x_actor, "case_created", case_id, f"ref={ref}")
    await db.commit()
    async with db.execute("SELECT * FROM cases WHERE id=?", (case_id,)) as cur:
        row = await cur.fetchone()
    return dict(row)


@router.get("/cases/{case_id}", response_model=CaseOut)
async def get_case(case_id: int, db: aiosqlite.Connection = Depends(get_db)):
    row = await _require_case(db, case_id)
    return dict(row)


@router.patch("/cases/{case_id}/status", response_model=CaseOut)
async def update_case_status(
    case_id: int,
    body: CaseStatusUpdate,
    x_actor: str = Header(...),
    db: aiosqlite.Connection = Depends(get_db),
):
    row = await _require_case(db, case_id)
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
    if target == "closed":
        await db.execute(
            "UPDATE cases SET status=?, closed_at=? WHERE id=?",
            (target, now, case_id),
        )
    else:
        await db.execute(
            "UPDATE cases SET status=?, closed_at=NULL WHERE id=?",
            (target, case_id),
        )
    await _audit(db, x_actor, "case_status_updated", case_id, f"{current}->{target}")
    await db.commit()
    async with db.execute("SELECT * FROM cases WHERE id=?", (case_id,)) as cur:
        updated = await cur.fetchone()
    return dict(updated)


@router.post("/cases/{case_id}/close", response_model=CaseOut)
async def close_case(
    case_id: int,
    x_actor: str = Header(...),
    db: aiosqlite.Connection = Depends(get_db),
):
    return await update_case_status(
        case_id, CaseStatusUpdate(status="closed"), x_actor, db
    )


@router.get("/cases/{case_id}/alcoa-gaps", response_model=List[AlcoaGapOut])
async def list_gaps(case_id: int, db: aiosqlite.Connection = Depends(get_db)):
    await _require_case(db, case_id)
    async with db.execute(
        "SELECT * FROM alcoa_gaps WHERE case_id=? ORDER BY id", (case_id,)
    ) as cur:
        rows = await cur.fetchall()
    return [dict(r) for r in rows]


@router.post("/cases/{case_id}/alcoa-gaps", response_model=AlcoaGapOut, status_code=201)
async def add_gap(
    case_id: int,
    body: AlcoaGapCreate,
    x_actor: str = Header(...),
    db: aiosqlite.Connection = Depends(get_db),
):
    await _require_open_case(db, case_id)
    now = _now()
    await db.execute(
        "INSERT INTO alcoa_gaps (case_id,attribute,gap_found,observation,assessed_by,assessed_at) VALUES (?,?,?,?,?,?)",
        (case_id, body.attribute, int(body.gap_found), body.observation, body.assessed_by, now),
    )
    async with db.execute("SELECT last_insert_rowid()") as cur:
        gap_id = (await cur.fetchone())[0]
    await _audit(
        db, x_actor, "alcoa_gap_recorded", case_id,
        f"attribute={body.attribute} gap={body.gap_found}",
    )
    await db.commit()
    async with db.execute("SELECT * FROM alcoa_gaps WHERE id=?", (gap_id,)) as cur:
        row = await cur.fetchone()
    return dict(row)


@router.get("/cases/{case_id}/evidence", response_model=List[EvidenceOut])
async def list_evidence(case_id: int, db: aiosqlite.Connection = Depends(get_db)):
    await _require_case(db, case_id)
    async with db.execute(
        "SELECT * FROM evidence_log WHERE case_id=? ORDER BY id", (case_id,)
    ) as cur:
        rows = await cur.fetchall()
    return [dict(r) for r in rows]


@router.post("/cases/{case_id}/evidence", response_model=EvidenceOut, status_code=201)
async def add_evidence(
    case_id: int,
    body: EvidenceCreate,
    x_actor: str = Header(...),
    db: aiosqlite.Connection = Depends(get_db),
):
    await _require_open_case(db, case_id)
    now = _now()
    await db.execute(
        "INSERT INTO evidence_log (case_id,evidence_type,description,recorded_by,recorded_at) VALUES (?,?,?,?,?)",
        (case_id, body.evidence_type, body.description, body.recorded_by, now),
    )
    async with db.execute("SELECT last_insert_rowid()") as cur:
        eid = (await cur.fetchone())[0]
    await _audit(db, x_actor, "evidence_recorded", case_id, f"type={body.evidence_type}")
    await db.commit()
    async with db.execute("SELECT * FROM evidence_log WHERE id=?", (eid,)) as cur:
        row = await cur.fetchone()
    return dict(row)


@router.get("/cases/{case_id}/capas", response_model=List[CapaOut])
async def list_capas(case_id: int, db: aiosqlite.Connection = Depends(get_db)):
    await _require_case(db, case_id)
    async with db.execute(
        "SELECT * FROM capas WHERE case_id=? ORDER BY id", (case_id,)
    ) as cur:
        rows = await cur.fetchall()
    return [dict(r) for r in rows]


@router.post("/cases/{case_id}/capas", response_model=CapaOut, status_code=201)
async def add_capa(
    case_id: int,
    body: CapaCreate,
    x_actor: str = Header(...),
    db: aiosqlite.Connection = Depends(get_db),
):
    await _require_open_case(db, case_id)
    ref = _ref("CAPA")
    now = _now()
    await db.execute(
        "INSERT INTO capas (case_id,capa_ref,action_type,description,owner,due_date,status,created_at) VALUES (?,?,?,?,?,?,?,?)",
        (case_id, ref, body.action_type, body.description, body.owner, body.due_date, "open", now),
    )
    async with db.execute("SELECT last_insert_rowid()") as cur:
        cid = (await cur.fetchone())[0]
    await _audit(db, x_actor, "capa_created", case_id, f"ref={ref} type={body.action_type}")
    await db.commit()
    async with db.execute("SELECT * FROM capas WHERE id=?", (cid,)) as cur:
        row = await cur.fetchone()
    return dict(row)


@router.patch("/cases/{case_id}/capas/{capa_id}/status", response_model=CapaOut)
async def update_capa_status(
    case_id: int,
    capa_id: int,
    body: CapaStatusUpdate,
    x_actor: str = Header(...),
    db: aiosqlite.Connection = Depends(get_db),
):
    await _require_open_case(db, case_id)
    async with db.execute(
        "SELECT * FROM capas WHERE id=? AND case_id=?", (capa_id, case_id)
    ) as cur:
        row = await cur.fetchone()
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
    await db.execute("UPDATE capas SET status=? WHERE id=?", (target, capa_id))
    await _audit(
        db, x_actor, "capa_status_updated", case_id,
        f"capa={row['capa_ref']} {current}->{target}",
    )
    await db.commit()
    async with db.execute("SELECT * FROM capas WHERE id=?", (capa_id,)) as cur:
        updated = await cur.fetchone()
    return dict(updated)


@router.get("/audit-log", response_model=List[AuditEntry])
async def audit_log(
    case_id: Optional[int] = None,
    db: aiosqlite.Connection = Depends(get_db),
):
    if case_id:
        async with db.execute(
            "SELECT * FROM audit_log WHERE case_id=? ORDER BY id DESC", (case_id,)
        ) as cur:
            rows = await cur.fetchall()
    else:
        async with db.execute(
            "SELECT * FROM audit_log ORDER BY id DESC LIMIT 200"
        ) as cur:
            rows = await cur.fetchall()
    return [dict(r) for r in rows]


def _serialize_ai_suggestion(row) -> dict:
    payload = json.loads(row["response_json"])
    # Recompute the SHA-256 over the stored payload and compare against the
    # hash recorded at generation time. hash_response() uses sort_keys=True,
    # so this is stable across the json.dumps/json.loads round trip and
    # actually detects tampering or corruption rather than just storing a
    # hash that's never checked again.
    integrity_verified = hash_response(payload) == row["response_hash"]
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
        "integrity_verified": integrity_verified,
    }


@router.post("/cases/{case_id}/ai-suggest-gaps", response_model=AiSuggestionOut, status_code=201)
async def ai_suggest_gaps(
    case_id: int,
    x_actor: str = Header(...),
    db: aiosqlite.Connection = Depends(get_db),
):
    case_row = await _require_open_case(db, case_id)
    try:
        result = await generate_gap_suggestions(
            case_row["title"], case_row["system"], case_row["signal_type"]
        )
    except AiUnavailableError as exc:
        raise HTTPException(status_code=503, detail=f"AI assistant unavailable: {exc}")
    payload = result.model_dump()
    response_hash = hash_response(payload)
    now = _now()
    await db.execute(
        """
        INSERT INTO ai_suggestions
        (case_id, model_name, model_provider, prompt_version, response_json, response_hash, generated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (case_id, OLLAMA_MODEL, "local_ollama", PROMPT_VERSION, json.dumps(payload), response_hash, now),
    )
    async with db.execute("SELECT last_insert_rowid()") as cur:
        suggestion_id = (await cur.fetchone())[0]
    await _audit(
        db, x_actor, "ai_suggestion_generated", case_id,
        f"model={OLLAMA_MODEL} hash={response_hash[:12]}",
    )
    await db.commit()
    async with db.execute("SELECT * FROM ai_suggestions WHERE id=?", (suggestion_id,)) as cur:
        row = await cur.fetchone()
    return _serialize_ai_suggestion(row)


@router.get("/cases/{case_id}/ai-suggestions", response_model=List[AiSuggestionOut])
async def list_ai_suggestions(case_id: int, db: aiosqlite.Connection = Depends(get_db)):
    await _require_case(db, case_id)
    async with db.execute(
        "SELECT * FROM ai_suggestions WHERE case_id=? ORDER BY id DESC", (case_id,)
    ) as cur:
        rows = await cur.fetchall()
    return [_serialize_ai_suggestion(r) for r in rows]


@router.post("/ai-suggestions/{suggestion_id}/review", response_model=AiSuggestionReviewResult)
async def review_ai_suggestion(
    suggestion_id: int,
    body: AiSuggestionReviewCreate,
    x_actor: str = Header(...),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Record a human review decision on an AI suggestion.

    - 'accepted' writes one alcoa_gaps row per suggested attribute — this is
      the actual gated write the README describes ("every suggestion
      requires explicit human action before any gap is recorded").
    - 'rejected' / 'modified' record the decision but write nothing to
      alcoa_gaps; a modified assessment goes through the normal manual
      "Record gap assessment" form so the human's edited wording is what
      ends up on the record, not a second copy of the AI's rationale.
    - A suggestion can only be reviewed once (idempotency guard below) —
      re-reviewing previously silently overwrote human_action/reviewed_by
      with no trace of the prior decision, which doesn't fit an
      append-only audit trail.
    """
    async with db.execute("SELECT * FROM ai_suggestions WHERE id=?", (suggestion_id,)) as cur:
        row = await cur.fetchone()
    if not row:
        raise HTTPException(404, "AI suggestion not found")
    await _require_open_case(db, row["case_id"])

    if row["human_action"] is not None:
        raise HTTPException(
            409,
            f"This AI suggestion was already reviewed ({row['human_action']} "
            f"by {row['reviewed_by']} at {row['reviewed_at']})",
        )

    payload = json.loads(row["response_json"])
    if hash_response(payload) != row["response_hash"]:
        raise HTTPException(
            500,
            "Stored AI suggestion failed integrity verification (SHA-256 mismatch); "
            "refusing to act on it. This indicates data corruption or tampering.",
        )

    now = _now()
    gaps_recorded: List[dict] = []
    if body.human_action == "accepted":
        for item in payload.get("suggestions", []):
            observation = (
                f"AI-suggested ({item['risk_level']} risk, accepted by reviewer): "
                f"{item['rationale']}"
            )
            await db.execute(
                "INSERT INTO alcoa_gaps (case_id,attribute,gap_found,observation,assessed_by,assessed_at) "
                "VALUES (?,?,?,?,?,?)",
                (row["case_id"], item["attribute"], 1, observation, body.reviewed_by, now),
            )
            async with db.execute("SELECT last_insert_rowid()") as cur:
                gap_id = (await cur.fetchone())[0]
            async with db.execute("SELECT * FROM alcoa_gaps WHERE id=?", (gap_id,)) as cur:
                gaps_recorded.append(dict(await cur.fetchone()))

    await db.execute(
        "UPDATE ai_suggestions SET human_action=?, reviewed_by=?, reviewed_at=? WHERE id=?",
        (body.human_action, body.reviewed_by, now, suggestion_id),
    )
    await _audit(
        db, x_actor, "ai_suggestion_reviewed", row["case_id"],
        f"action={body.human_action} gaps_recorded={len(gaps_recorded)}",
    )
    await db.commit()
    async with db.execute("SELECT * FROM ai_suggestions WHERE id=?", (suggestion_id,)) as cur:
        updated = await cur.fetchone()
    return {
        "suggestion": _serialize_ai_suggestion(updated),
        "gaps_recorded": gaps_recorded,
    }
