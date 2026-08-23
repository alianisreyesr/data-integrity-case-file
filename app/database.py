"""SQLite access — shared async connection + sync helpers for seed/Docker.

Optimizations:
- Single long-lived aiosqlite connection for the API process (SQLite-friendly)
- WAL, busy_timeout, foreign_keys, NORMAL sync, larger cache
- Indexes on foreign keys and status columns
- FastAPI Depends(get_db) injects the shared connection per request
"""
from __future__ import annotations

import os
import sqlite3
from typing import Any, AsyncIterator, Optional

import aiosqlite

DB_PATH = os.getenv("DB_PATH", "data/di_cases.db")

# Tunables (override via env for demos under load)
BUSY_TIMEOUT_MS = int(os.getenv("SQLITE_BUSY_TIMEOUT_MS", "5000"))
CACHE_SIZE_KIB = int(os.getenv("SQLITE_CACHE_SIZE_KIB", "-64000"))  # negative = KiB

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

CREATE INDEX IF NOT EXISTS idx_cases_status ON cases(status);
CREATE INDEX IF NOT EXISTS idx_alcoa_gaps_case_id ON alcoa_gaps(case_id);
CREATE INDEX IF NOT EXISTS idx_evidence_case_id ON evidence_log(case_id);
CREATE INDEX IF NOT EXISTS idx_capas_case_id ON capas(case_id);
CREATE INDEX IF NOT EXISTS idx_capas_status ON capas(status);
CREATE INDEX IF NOT EXISTS idx_audit_case_id ON audit_log(case_id);
CREATE INDEX IF NOT EXISTS idx_ai_suggestions_case_id ON ai_suggestions(case_id);
CREATE INDEX IF NOT EXISTS idx_ai_item_reviews_suggestion ON ai_suggestion_item_reviews(suggestion_id);
"""

# Process-wide shared connection (opened in lifespan)
_db: Optional[aiosqlite.Connection] = None


def _ensure_dir() -> None:
    parent = os.path.dirname(DB_PATH)
    if parent:
        os.makedirs(parent, exist_ok=True)


async def _configure_connection(db: aiosqlite.Connection) -> None:
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute(f"PRAGMA busy_timeout={BUSY_TIMEOUT_MS}")
    await db.execute("PRAGMA foreign_keys=ON")
    await db.execute("PRAGMA synchronous=NORMAL")
    await db.execute(f"PRAGMA cache_size={CACHE_SIZE_KIB}")
    await db.execute("PRAGMA temp_store=MEMORY")
    await db.execute("PRAGMA mmap_size=268435456")  # 256 MiB hint; ignored if unsupported


def row_to_dict(row: Optional[aiosqlite.Row | sqlite3.Row]) -> Optional[dict[str, Any]]:
    if row is None:
        return None
    return dict(row)


async def connect() -> aiosqlite.Connection:
    """Open and configure the shared API connection (call once at startup)."""
    global _db
    _ensure_dir()
    if _db is not None:
        return _db
    _db = await aiosqlite.connect(DB_PATH)
    await _configure_connection(_db)
    return _db


async def disconnect() -> None:
    global _db
    if _db is not None:
        await _db.close()
        _db = None


async def get_db() -> AsyncIterator[aiosqlite.Connection]:
    """FastAPI dependency: yield the shared connection (no per-request open/close)."""
    if _db is None:
        await connect()
    assert _db is not None
    yield _db


async def init_db() -> None:
    """Create schema/indexes and ensure shared connection is ready."""
    db = await connect()
    await db.executescript(SCHEMA)
    await db.commit()


# ── Sync helpers (seed.py, Dockerfile RUN) ────────────────────────────────────

def _configure_sync(conn: sqlite3.Connection) -> None:
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(f"PRAGMA busy_timeout={BUSY_TIMEOUT_MS}")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA synchronous=NORMAL")


def get_connection() -> sqlite3.Connection:
    _ensure_dir()
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    _configure_sync(conn)
    return conn


def init_db_sync() -> None:
    conn = get_connection()
    with conn:
        conn.executescript(SCHEMA)
    conn.close()
