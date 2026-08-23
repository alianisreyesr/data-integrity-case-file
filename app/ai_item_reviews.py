"""Per-item AI suggestion reviews (async, shared DB connection)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Literal, Optional

import aiosqlite
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field, model_validator

from .database import get_db

router = APIRouter()
ALCOA = Literal[
    "Attributable", "Legible", "Contemporaneous", "Original", "Accurate",
    "Complete", "Consistent", "Enduring", "Available",
]
RISK = Literal["low", "medium", "high"]
ACTION = Literal["accepted", "rejected", "modified"]


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


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


@router.get("/ai-suggestions/{suggestion_id}/items")
async def list_items(
    suggestion_id: int,
    db: aiosqlite.Connection = Depends(get_db),
):
    async with db.execute("SELECT * FROM ai_suggestions WHERE id=?", (suggestion_id,)) as cur:
        suggestion = await cur.fetchone()
    if not suggestion:
        raise HTTPException(404, "AI suggestion not found")
    source = json.loads(suggestion["response_json"]).get("suggestions", [])
    async with db.execute(
        "SELECT * FROM ai_suggestion_item_reviews WHERE suggestion_id=?", (suggestion_id,)
    ) as cur:
        reviews = await cur.fetchall()
    by_index = {row["item_index"]: dict(row) for row in reviews}
    return [
        {"item_index": index, "original": item, "review": by_index.get(index)}
        for index, item in enumerate(source)
    ]


@router.post("/ai-suggestions/{suggestion_id}/items/{item_index}/review", status_code=201)
async def review_item(
    suggestion_id: int,
    item_index: int,
    body: ItemReviewCreate,
    x_actor: str = Header(...),
    db: aiosqlite.Connection = Depends(get_db),
):
    async with db.execute("SELECT * FROM ai_suggestions WHERE id=?", (suggestion_id,)) as cur:
        suggestion = await cur.fetchone()
    if not suggestion:
        raise HTTPException(404, "AI suggestion not found")
    items = json.loads(suggestion["response_json"]).get("suggestions", [])
    if item_index < 0 or item_index >= len(items):
        raise HTTPException(404, "AI suggestion item not found")
    item = items[item_index]

    async with db.execute(
        "SELECT id FROM ai_suggestion_item_reviews WHERE suggestion_id=? AND item_index=?",
        (suggestion_id, item_index),
    ) as cur:
        existing = await cur.fetchone()
    if existing:
        raise HTTPException(409, "This AI suggestion item has already been reviewed")

    reviewed_at = now()
    await db.execute(
        """INSERT INTO ai_suggestion_item_reviews
        (suggestion_id,item_index,original_attribute,original_risk_level,original_rationale,
         action,final_attribute,final_risk_level,final_rationale,reviewer_comment,reviewed_by,reviewed_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            suggestion_id, item_index, item["attribute"], item["risk_level"], item["rationale"],
            body.action, body.final_attribute, body.final_risk_level, body.final_rationale,
            body.reviewer_comment, body.reviewed_by, reviewed_at,
        ),
    )
    await db.execute(
        "INSERT INTO audit_log (case_id,actor,action,detail,created_at) VALUES (?,?,?,?,?)",
        (
            suggestion["case_id"], x_actor, "ai_suggestion_item_reviewed",
            f"suggestion={suggestion_id}; item={item_index}; action={body.action}", reviewed_at,
        ),
    )
    await db.commit()
    async with db.execute(
        "SELECT * FROM ai_suggestion_item_reviews WHERE suggestion_id=? AND item_index=?",
        (suggestion_id, item_index),
    ) as cur:
        review = await cur.fetchone()
    return {"item_index": item_index, "original": item, "review": dict(review)}
