"""Inbox folder watcher — picks up new AIMS DayRepReport files.

This is the lowest-friction integration: instead of requiring AIMS API
or SFTP credentials, a small system task can drop new exports into a
configured directory (often a Windows network share mounted on the
deploy host). The watcher polls the directory, processes each new
file once, and records the run in the persistence layer.

Designed to run periodically (cron / systemd timer / Streamlit
``st.experimental_rerun`` schedule). It does not maintain its own
event loop — each call returns the set of new files processed since
the last call.
"""

from __future__ import annotations

import hashlib
import logging
import sqlite3
from dataclasses import dataclass, field
from datetime import date, time
from pathlib import Path

from src.cascade.cascade_detector import compute_kpis, detect_cascade_multi
from src.cascade.ranking import compute_priority
from src.impact import estimate_pax_and_cost
from src.models.event import AirportClosureEvent
from src.parser.dayrep_parser import parse_dayrep_report
from src.persistence import record_audit_event, record_run

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class WatcherConfig:
    """Configuration for one watch session."""

    inbox_dir: Path
    glob: str = "*.xlsx"
    default_events: tuple[AirportClosureEvent, ...] = field(default_factory=tuple)
    user: str = "watcher"


@dataclass
class WatcherResult:
    """Summary of what one poll found and processed."""

    files_processed: list[Path] = field(default_factory=list)
    files_skipped: list[Path] = field(default_factory=list)
    runs_created: list[int] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def _hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def _processed_hashes(conn: sqlite3.Connection) -> set[str]:
    """Return the set of file hashes that have already been recorded."""
    rows = conn.execute("SELECT file_hashes FROM runs").fetchall()
    seen: set[str] = set()
    for r in rows:
        try:
            import json

            for h in json.loads(r["file_hashes"]):
                seen.add(str(h))
        except (TypeError, ValueError):
            continue
    return seen


def poll_inbox_once(
    conn: sqlite3.Connection,
    config: WatcherConfig,
) -> WatcherResult:
    """Scan ``config.inbox_dir`` and process previously-unseen files.

    Skips files whose hash has already been recorded in the runs table
    so re-running this is idempotent. If no default closure events are
    configured, files are parsed but no cascade run is recorded — the
    operator can still inspect the file list manually.
    """
    result = WatcherResult()

    if not config.inbox_dir.exists():
        result.errors.append(f"inbox_dir does not exist: {config.inbox_dir}")
        return result

    seen = _processed_hashes(conn)

    for path in sorted(config.inbox_dir.glob(config.glob)):
        try:
            file_hash = _hash_file(path)
        except OSError as exc:
            result.errors.append(f"hash_failed({path.name}): {exc}")
            continue

        if file_hash in seen:
            result.files_skipped.append(path)
            continue

        try:
            df, _warnings = parse_dayrep_report(str(path))
        except Exception as exc:  # noqa: BLE001 — never crash the watcher loop
            result.errors.append(f"parse_failed({path.name}): {exc}")
            continue

        if df.empty:
            result.files_skipped.append(path)
            continue

        if not config.default_events:
            result.files_processed.append(path)
            continue  # Defer to manual run, just record presence.

        df = detect_cascade_multi(df, list(config.default_events))
        df = compute_priority(df)
        df = estimate_pax_and_cost(df)
        kpis = compute_kpis(df)
        affected = df[df["impact_level_numeric"].notna()]
        kpis["total_pax_disrupted"] = int(affected["est_pax"].sum()) if not affected.empty else 0
        kpis["total_cost_usd"] = (
            float(affected["est_cost_usd"].sum()) if not affected.empty else 0.0
        )

        run_id = record_run(
            conn,
            user=config.user,
            file_hashes=[file_hash],
            closure_config=[
                {
                    "airport": e.airport,
                    "closure_date": str(e.closure_date),
                    "start_time": e.start_time.strftime("%H:%M"),
                    "end_time": e.end_time.strftime("%H:%M"),
                    "closure_type": e.closure_type,
                }
                for e in config.default_events
            ],
            kpi_snapshot={k: v for k, v in kpis.items() if isinstance(v, (int, float))},
            notes=f"watcher: {path.name}",
        )
        record_audit_event(
            conn,
            user=config.user,
            action="watcher_run",
            payload={"run_id": run_id, "file": path.name, "hash": file_hash},
        )
        result.files_processed.append(path)
        result.runs_created.append(run_id)
        seen.add(file_hash)

    logger.info(
        "watcher_poll_complete",
        extra={
            "processed": len(result.files_processed),
            "skipped": len(result.files_skipped),
            "errors": len(result.errors),
        },
    )
    return result


# Re-export here so test imports don't need to know it lives in the
# stdlib's ``datetime``.
__all__ = ["WatcherConfig", "WatcherResult", "poll_inbox_once", "date", "time"]
