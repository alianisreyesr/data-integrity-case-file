"""Per-item, human-editable review records for AI-generated suggestions."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, Field, model_validator

from .database import get_connection

router = APIRouter()
ALCOA = Literal["Attributable", "Legible", "Contemporaneous", "Original", "Accurate", "Complete", "Consistent", "Enduring", "Available"]
RISK = Literal["low", "medium", "high"]
ACTION = Literal["accepted", "rejected", "modified"]


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def init_ai_item_review_db() -> None:
    conn = get_connection()
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ai_suggestion_item_reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                suggestion_id INTEGER NOT NULL REFERENCES ai_suggestions(id),
                item_index INTEGER NOT NULL,
                original_attribute TEXT NOT NULL,
                original_risk_level TEXT NOT NULL,
                original_rationale TEXT NOT NULL,
                action TEXT NOT NULL,
                final_attribute TEXT NOT NULL,
                final_risk_level TEXT NOT NULL,
                final_rationale TEXT NOT NULL,
                reviewer_comment TEXT,
                reviewed_by TEXT NOT NULL,
                reviewed_at TEXT NOT NULL,
                UNIQUE(suggestion_id, item_index)
            )
        """)
    conn.close()


class ItemReviewCreate(BaseModel):
    action: ACTION
    final_attribute: ALCOA
    final_risk_level: RISK
    final_rationale: str = Field(..., min_length=5, max_length=1000)
    reviewer_comment: Optional[str] = Field(None, max_length=1000)
    reviewed_by: str = Field(..., min_length=2, max_length=80)

    @model_validator(mode="after")
    def comment_for_non_acceptance(self):
        if self.action in {"rejected", "modified"} and not (self.reviewer_comment or "").strip():
            raise ValueError("Reviewer comment is required when rejecting or modifying a suggestion.")
        return self


def source_item(conn, suggestion_id: int, item_index: int) -> tuple[dict, object]:
    suggestion = conn.execute("SELECT * FROM ai_suggestions WHERE id=?", (suggestion_id,)).fetchone()
    if not suggestion:
        raise HTTPException(404, "AI suggestion not found")
    items = json.loads(suggestion["response_json"]).get("suggestions", [])
    if item_index < 0 or item_index >= len(items):
        raise HTTPException(404, "AI suggestion item not found")
    return items[item_index], suggestion


@router.get("/ai-suggestions/{suggestion_id}/items")
def list_items(suggestion_id: int):
    conn = get_connection()
    try:
        suggestion = conn.execute("SELECT * FROM ai_suggestions WHERE id=?", (suggestion_id,)).fetchone()
        if not suggestion:
            raise HTTPException(404, "AI suggestion not found")
        source = json.loads(suggestion["response_json"]).get("suggestions", [])
        reviews = conn.execute("SELECT * FROM ai_suggestion_item_reviews WHERE suggestion_id=?", (suggestion_id,)).fetchall()
        by_index = {row["item_index"]: dict(row) for row in reviews}
        return [{"item_index": index, "original": item, "review": by_index.get(index)} for index, item in enumerate(source)]
    finally:
        conn.close()


@router.post("/ai-suggestions/{suggestion_id}/items/{item_index}/review", status_code=201)
def review_item(suggestion_id: int, item_index: int, body: ItemReviewCreate, x_actor: str = Header(...)):
    conn = get_connection()
    try:
        item, suggestion = source_item(conn, suggestion_id, item_index)
        existing = conn.execute("SELECT id FROM ai_suggestion_item_reviews WHERE suggestion_id=? AND item_index=?", (suggestion_id, item_index)).fetchone()
        if existing:
            raise HTTPException(409, "This AI suggestion item has already been reviewed")
        reviewed_at = now()
        with conn:
            conn.execute(
                """INSERT INTO ai_suggestion_item_reviews
                (suggestion_id,item_index,original_attribute,original_risk_level,original_rationale,action,final_attribute,final_risk_level,final_rationale,reviewer_comment,reviewed_by,reviewed_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (suggestion_id, item_index, item["attribute"], item["risk_level"], item["rationale"], body.action, body.final_attribute, body.final_risk_level, body.final_rationale, body.reviewer_comment, body.reviewed_by, reviewed_at),
            )
            conn.execute(
                "INSERT INTO audit_log (case_id,actor,action,detail,created_at) VALUES (?,?,?,?,?)",
                (suggestion["case_id"], x_actor, "ai_suggestion_item_reviewed", f"suggestion={suggestion_id}; item={item_index}; action={body.action}", reviewed_at),
            )
        review = conn.execute("SELECT * FROM ai_suggestion_item_reviews WHERE suggestion_id=? AND item_index=?", (suggestion_id, item_index)).fetchone()
        return {"item_index": item_index, "original": item, "review": dict(review)}
    finally:
        conn.close()
