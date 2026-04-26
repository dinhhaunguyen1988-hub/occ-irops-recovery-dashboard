"""Low-level SQLite connection + schema setup."""

from __future__ import annotations

import sqlite3
from pathlib import Path

DEFAULT_DB_PATH = Path("data") / "runs.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user            TEXT    NOT NULL,
    created_at      TEXT    NOT NULL,
    file_hashes     TEXT    NOT NULL,
    closure_config  TEXT    NOT NULL,
    kpi_snapshot    TEXT    NOT NULL,
    notes           TEXT
);

CREATE INDEX IF NOT EXISTS ix_runs_created_at ON runs(created_at DESC);
CREATE INDEX IF NOT EXISTS ix_runs_user ON runs(user);

CREATE TABLE IF NOT EXISTS settings (
    key             TEXT    PRIMARY KEY,
    value           TEXT    NOT NULL,
    updated_at      TEXT    NOT NULL,
    updated_by      TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_events (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user            TEXT    NOT NULL,
    action          TEXT    NOT NULL,
    payload         TEXT,
    created_at      TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_audit_created_at ON audit_events(created_at DESC);
CREATE INDEX IF NOT EXISTS ix_audit_user ON audit_events(user);
"""


def get_connection(db_path: str | Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Return a SQLite connection with row factory set to dict-like rows.

    The parent directory is created on demand so callers don't have to
    bootstrap ``data/`` themselves. Schema is applied lazily by
    :func:`init_db` (called on first connect from the app).
    """
    db_file = Path(db_path)
    db_file.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_file))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    """Create tables + indexes if they don't already exist."""
    conn.executescript(_SCHEMA)
    conn.commit()
