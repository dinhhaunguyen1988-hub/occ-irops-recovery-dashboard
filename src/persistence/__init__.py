"""SQLite persistence for runs, settings, and audit events.

Sprint 5 production-deploy module. The persistence layer stores three
tables in a single SQLite file (default ``data/runs.db``):

- ``runs``: one row per cascade analysis run (closure config, KPI
  snapshot, file hash, user, timestamp). Lets DMs review past
  decisions and compare against today.
- ``settings``: key-value table for tunable assumptions (load factor,
  cost per pax per minute, aircraft seat capacity overrides).
- ``audit_events``: append-only log of user actions for IT/compliance.

Schema is created on first connect; migrations are deliberately *not*
required for MVP — the schema only grows additively.
"""

from src.persistence.audit import (
    list_audit_events,
    record_audit_event,
)
from src.persistence.db import get_connection, init_db
from src.persistence.runs import (
    list_recent_runs,
    record_run,
)
from src.persistence.settings import (
    DEFAULT_SETTINGS,
    SettingsDict,
    get_settings,
    update_settings,
)

__all__ = [
    "DEFAULT_SETTINGS",
    "SettingsDict",
    "get_connection",
    "init_db",
    "list_audit_events",
    "list_recent_runs",
    "record_audit_event",
    "record_run",
    "get_settings",
    "update_settings",
]
