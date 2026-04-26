"""Persist + retrieve cascade analysis runs.

Each run records the closure configuration (so the same analysis can be
reproduced later), the KPI snapshot (so trend comparisons are cheap),
and the file hashes (so we know which AIMS export was analysed without
storing the raw file).
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any


def record_run(
    conn: sqlite3.Connection,
    *,
    user: str,
    file_hashes: list[str],
    closure_config: list[dict[str, Any]],
    kpi_snapshot: dict[str, Any],
    notes: str | None = None,
) -> int:
    """Insert a run row and return its primary key.

    All complex fields are stored as JSON for forward-compatibility — the
    schema does not need to evolve when we add new KPI fields or closure
    types in later sprints.
    """
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    cursor = conn.execute(
        """
        INSERT INTO runs (user, created_at, file_hashes, closure_config, kpi_snapshot, notes)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            user,
            now,
            json.dumps(file_hashes),
            json.dumps(closure_config, default=str),
            json.dumps(kpi_snapshot, default=str),
            notes,
        ),
    )
    conn.commit()
    return int(cursor.lastrowid or 0)


def list_recent_runs(
    conn: sqlite3.Connection,
    limit: int = 20,
    user: str | None = None,
) -> list[dict[str, Any]]:
    """Return up to ``limit`` recent runs, newest first.

    JSON-encoded fields are deserialised so callers can render directly.
    Optional ``user`` filter is used by the "My runs" tab in the
    dashboard.
    """
    if user is not None:
        rows = conn.execute(
            "SELECT id, user, created_at, file_hashes, closure_config, kpi_snapshot, notes "
            "FROM runs WHERE user = ? ORDER BY created_at DESC, id DESC LIMIT ?",
            (user, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT id, user, created_at, file_hashes, closure_config, kpi_snapshot, notes "
            "FROM runs ORDER BY created_at DESC, id DESC LIMIT ?",
            (limit,),
        ).fetchall()

    return [
        {
            "id": int(r["id"]),
            "user": r["user"],
            "created_at": r["created_at"],
            "file_hashes": json.loads(r["file_hashes"]),
            "closure_config": json.loads(r["closure_config"]),
            "kpi_snapshot": json.loads(r["kpi_snapshot"]),
            "notes": r["notes"],
        }
        for r in rows
    ]
