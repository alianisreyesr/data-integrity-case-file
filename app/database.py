"""SQLite access — async path for the API, sync path for seed/Docker build."""
from __future__ import annotations

import os
import sqlite3
from typing import Any, AsyncIterator, Optional

import aiosqlite

DB_PATH = os.getenv("DB_PATH", "data/di_cases.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS cases (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    case_ref    TEXT    NOT NULL UNIQUE,
    title       TEXT    NOT NULL,
    system      TEXT    NOT NULL,
    signal_type TEXT    NOT NULL,
    status      TEXT    NOT NULL DEFAULT 'intake',
    opened_by   TEXT    NOT NULL,
    opened_at   TEXT    NOT NULL,
    closed_at   TEXT
);

CREATE TABLE IF NOT EXISTS alcoa_gaps (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id     INTEGER NOT NULL REFERENCES cases(id),
    attribute   TEXT    NOT NULL,
    gap_found   INTEGER NOT NULL DEFAULT 0,
    observation TEXT,
    assessed_by TEXT    NOT NULL,
    assessed_at TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS evidence_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id     INTEGER NOT NULL REFERENCES cases(id),
    evidence_type TEXT  NOT NULL,
    description TEXT    NOT NULL,
    recorded_by TEXT    NOT NULL,
    recorded_at TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS capas (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id      INTEGER NOT NULL REFERENCES cases(id),
    capa_ref     TEXT    NOT NULL UNIQUE,
    action_type  TEXT    NOT NULL,
    description  TEXT    NOT NULL,
    owner        TEXT    NOT NULL,
    due_date     TEXT    NOT NULL,
    status       TEXT    NOT NULL DEFAULT 'open',
    created_at   TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id     INTEGER,
    actor       TEXT    NOT NULL,
    action      TEXT    NOT NULL,
    detail      TEXT,
    created_at  TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS ai_suggestions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id         INTEGER NOT NULL REFERENCES cases(id),
    model_name      TEXT    NOT NULL,
    model_provider  TEXT    NOT NULL,
    prompt_version  TEXT    NOT NULL,
    response_json   TEXT    NOT NULL,
    response_hash   TEXT    NOT NULL,
    generated_at    TEXT    NOT NULL,
    human_action    TEXT,
    reviewed_by     TEXT,
    reviewed_at     TEXT
);

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
);
"""


def _ensure_dir() -> None:
    parent = os.path.dirname(DB_PATH)
    if parent:
        os.makedirs(parent, exist_ok=True)


def row_to_dict(row: Optional[aiosqlite.Row | sqlite3.Row]) -> Optional[dict[str, Any]]:
    if row is None:
        return None
    return dict(row)


# ── Async API (FastAPI handlers) ──────────────────────────────────────────────

async def get_db() -> AsyncIterator[aiosqlite.Connection]:
    """Async context-managed connection with Row factory and WAL."""
    _ensure_dir()
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    try:
        yield db
    finally:
        await db.close()


async def init_db() -> None:
    _ensure_dir()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(SCHEMA)
        await db.commit()


# ── Sync helpers (seed.py, Dockerfile RUN) ────────────────────────────────────

def get_connection() -> sqlite3.Connection:
    _ensure_dir()
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db_sync() -> None:
    conn = get_connection()
    with conn:
        conn.executescript(SCHEMA)
    conn.close()
