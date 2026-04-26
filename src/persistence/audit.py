"""Append-only audit event log for compliance / IT review."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any


def record_audit_event(
    conn: sqlite3.Connection,
    *,
    user: str,
    action: str,
    payload: dict[str, Any] | None = None,
) -> int:
    """Insert a single audit event and return its row id.

    ``action`` should be a short, machine-readable string such as
    ``login_success``, ``run_analysis``, ``settings_updated``,
    ``download_pdf``, ``download_excel``. ``payload`` is JSON-encoded
    metadata (kept small — never the raw file contents).
    """
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    cursor = conn.execute(
        "INSERT INTO audit_events (user, action, payload, created_at) VALUES (?, ?, ?, ?)",
        (
            user,
            action,
            json.dumps(payload, default=str) if payload is not None else None,
            now,
        ),
    )
    conn.commit()
    return int(cursor.lastrowid or 0)


def list_audit_events(
    conn: sqlite3.Connection,
    limit: int = 100,
    user: str | None = None,
    action: str | None = None,
) -> list[dict[str, Any]]:
    """Return up to ``limit`` audit events (newest first) with optional filters."""
    clauses: list[str] = []
    params: list[Any] = []
    if user is not None:
        clauses.append("user = ?")
        params.append(user)
    if action is not None:
        clauses.append("action = ?")
        params.append(action)
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    params.append(limit)

    rows = conn.execute(
        f"SELECT id, user, action, payload, created_at FROM audit_events {where} "
        f"ORDER BY created_at DESC, id DESC LIMIT ?",
        tuple(params),
    ).fetchall()

    return [
        {
            "id": int(r["id"]),
            "user": r["user"],
            "action": r["action"],
            "payload": json.loads(r["payload"]) if r["payload"] else None,
            "created_at": r["created_at"],
        }
        for r in rows
    ]
