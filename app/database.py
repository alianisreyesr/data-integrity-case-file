import sqlite3
import os

DB_PATH = os.getenv("DB_PATH", "data/di_cases.db")


def get_connection() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db() -> None:
    conn = get_connection()
    with conn:
        conn.executescript("""
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
        """)
    conn.close()
