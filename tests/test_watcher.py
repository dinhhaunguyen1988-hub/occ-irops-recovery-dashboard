"""Tests for the inbox folder watcher."""

from __future__ import annotations

import shutil
from pathlib import Path

from src.integration.watcher import WatcherConfig, poll_inbox_once
from src.persistence import get_connection, init_db, list_recent_runs

SAMPLE_FILE = Path("data/sample/sample_dayrep_24042026.xlsx")


def _conn(tmp_path):
    db = tmp_path / "test.db"
    conn = get_connection(db)
    init_db(conn)
    return conn


def test_missing_inbox_dir_returns_error(tmp_path) -> None:
    conn = _conn(tmp_path)
    cfg = WatcherConfig(inbox_dir=tmp_path / "does_not_exist")
    res = poll_inbox_once(conn, cfg)
    assert res.errors
    assert "does not exist" in res.errors[0]


def test_empty_inbox_dir_returns_no_errors(tmp_path) -> None:
    conn = _conn(tmp_path)
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    res = poll_inbox_once(conn, WatcherConfig(inbox_dir=inbox))
    assert res.files_processed == []
    assert res.files_skipped == []
    assert res.errors == []


def test_watcher_processes_new_file_without_default_events(tmp_path) -> None:
    """With no default_events, file is parsed but no run is recorded."""
    if not SAMPLE_FILE.exists():
        return  # Sample data lives next to the tests; skip if missing.

    conn = _conn(tmp_path)
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    shutil.copy(SAMPLE_FILE, inbox / SAMPLE_FILE.name)

    res = poll_inbox_once(conn, WatcherConfig(inbox_dir=inbox))
    assert len(res.files_processed) == 1
    assert res.runs_created == []
    assert list_recent_runs(conn) == []


def test_watcher_is_idempotent_via_file_hash(tmp_path) -> None:
    if not SAMPLE_FILE.exists():
        return

    from datetime import date, time

    from src.models.event import AirportClosureEvent

    conn = _conn(tmp_path)
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    shutil.copy(SAMPLE_FILE, inbox / SAMPLE_FILE.name)

    cfg = WatcherConfig(
        inbox_dir=inbox,
        default_events=(
            AirportClosureEvent(
                airport="HAN",
                closure_date=date(2026, 4, 24),
                start_time=time(14, 0),
                end_time=time(18, 0),
                closure_type="airport_closed",
            ),
        ),
    )
    res1 = poll_inbox_once(conn, cfg)
    assert len(res1.runs_created) == 1
    assert len(res1.files_processed) == 1

    # Second poll: same file, must be skipped via file-hash dedup.
    res2 = poll_inbox_once(conn, cfg)
    assert res2.runs_created == []
    assert len(res2.files_skipped) == 1
