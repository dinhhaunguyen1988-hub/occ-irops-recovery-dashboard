"""Tunable settings persisted in SQLite.

The dashboard exposes a Settings page (DM-only) so finance / ops can
adjust load factor, cost per pax per minute, and aircraft seat
capacity overrides without a code deploy.

Stored as a single JSON blob under the ``main`` key for simplicity —
the table schema can grow to per-key rows later if locking becomes a
concern.
"""

from __future__ import annotations

import copy
import json
import sqlite3
from datetime import datetime, timezone
from typing import TypedDict

from src.impact.pax_estimator import (
    DEFAULT_COST_PER_PAX_PER_MINUTE,
    DEFAULT_LOAD_FACTOR,
    DEFAULT_SEAT_CAPACITY,
    LEVEL_DELAY_MINUTES,
)

_SETTINGS_KEY = "main"


class SettingsDict(TypedDict):
    """Shape of the persisted settings JSON blob."""

    load_factor: float
    cost_per_pax_per_minute: float
    seat_capacity: dict[str, int]
    level_delay_minutes: dict[str, int]


DEFAULT_SETTINGS: SettingsDict = {
    "load_factor": DEFAULT_LOAD_FACTOR,
    "cost_per_pax_per_minute": DEFAULT_COST_PER_PAX_PER_MINUTE,
    "seat_capacity": dict(DEFAULT_SEAT_CAPACITY),
    # JSON keys must be strings, so we serialise level → minutes with str keys.
    "level_delay_minutes": {str(k): v for k, v in LEVEL_DELAY_MINUTES.items()},
}


def get_settings(conn: sqlite3.Connection) -> SettingsDict:
    """Return the current settings, falling back to defaults if unset."""
    row = conn.execute(
        "SELECT value FROM settings WHERE key = ?",
        (_SETTINGS_KEY,),
    ).fetchone()
    if row is None:
        return copy.deepcopy(DEFAULT_SETTINGS)
    try:
        loaded = json.loads(row["value"])
    except (TypeError, ValueError):
        return copy.deepcopy(DEFAULT_SETTINGS)
    merged: SettingsDict = copy.deepcopy(DEFAULT_SETTINGS)
    for k in merged:
        if k in loaded:
            merged[k] = loaded[k]  # type: ignore[literal-required]
    return merged


def update_settings(
    conn: sqlite3.Connection,
    new_settings: SettingsDict,
    updated_by: str,
) -> None:
    """Persist a full settings blob (upsert)."""
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    conn.execute(
        """
        INSERT INTO settings (key, value, updated_at, updated_by)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET
            value = excluded.value,
            updated_at = excluded.updated_at,
            updated_by = excluded.updated_by
        """,
        (
            _SETTINGS_KEY,
            json.dumps(new_settings),
            now,
            updated_by,
        ),
    )
    conn.commit()


def settings_to_estimator_kwargs(
    settings: SettingsDict,
) -> dict[str, object]:
    """Translate persisted settings into kwargs for ``estimate_pax_and_cost``."""
    return {
        "load_factor": float(settings["load_factor"]),
        "cost_per_pax_per_minute": float(settings["cost_per_pax_per_minute"]),
        "seat_capacity": {str(k).upper(): int(v) for k, v in settings["seat_capacity"].items()},
        "level_delay_minutes": {int(k): int(v) for k, v in settings["level_delay_minutes"].items()},
    }
