"""Tests for the SQLite persistence layer (Sprint 5)."""

from __future__ import annotations

from src.persistence import (
    DEFAULT_SETTINGS,
    get_connection,
    get_settings,
    init_db,
    list_audit_events,
    list_recent_runs,
    record_audit_event,
    record_run,
    update_settings,
)
from src.persistence.settings import settings_to_estimator_kwargs


def _conn(tmp_path):
    db = tmp_path / "test.db"
    conn = get_connection(db)
    init_db(conn)
    return conn


# ---------------------------------------------------------------------------
# Schema bootstrap
# ---------------------------------------------------------------------------


def test_init_db_creates_three_tables(tmp_path) -> None:
    conn = _conn(tmp_path)
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    names = {r["name"] for r in rows}
    assert {"runs", "settings", "audit_events"} <= names


def test_init_db_is_idempotent(tmp_path) -> None:
    conn = _conn(tmp_path)
    init_db(conn)
    init_db(conn)  # must not error


# ---------------------------------------------------------------------------
# runs
# ---------------------------------------------------------------------------


def test_record_run_round_trips_complex_payload(tmp_path) -> None:
    conn = _conn(tmp_path)
    closure = [
        {
            "airport": "HAN",
            "closure_date": "2026-04-24",
            "start_time": "14:00",
            "end_time": "18:00",
        },
    ]
    kpi = {"affected_flights": 139, "level_1_count": 51, "total_cost_usd": 1898730.0}
    rid = record_run(
        conn, user="dm1", file_hashes=["abc123"], closure_config=closure, kpi_snapshot=kpi
    )
    assert rid > 0
    runs = list_recent_runs(conn, limit=10)
    assert len(runs) == 1
    assert runs[0]["user"] == "dm1"
    assert runs[0]["closure_config"] == closure
    assert runs[0]["kpi_snapshot"] == kpi


def test_list_recent_runs_orders_newest_first(tmp_path) -> None:
    conn = _conn(tmp_path)
    for i in range(3):
        record_run(
            conn,
            user="dm1",
            file_hashes=[f"h{i}"],
            closure_config=[{"airport": "HAN"}],
            kpi_snapshot={"affected_flights": i},
        )
    runs = list_recent_runs(conn, limit=5)
    # Newest first
    assert [r["kpi_snapshot"]["affected_flights"] for r in runs] == [2, 1, 0]


def test_list_recent_runs_filters_by_user(tmp_path) -> None:
    conn = _conn(tmp_path)
    record_run(
        conn,
        user="dm1",
        file_hashes=[],
        closure_config=[],
        kpi_snapshot={"affected_flights": 1},
    )
    record_run(
        conn,
        user="viewer1",
        file_hashes=[],
        closure_config=[],
        kpi_snapshot={"affected_flights": 2},
    )
    only_dm = list_recent_runs(conn, user="dm1")
    assert {r["user"] for r in only_dm} == {"dm1"}


# ---------------------------------------------------------------------------
# audit
# ---------------------------------------------------------------------------


def test_audit_event_is_persisted_with_payload(tmp_path) -> None:
    conn = _conn(tmp_path)
    record_audit_event(
        conn,
        user="dm1",
        action="run_analysis",
        payload={"events": [{"airport": "HAN"}]},
    )
    events = list_audit_events(conn, limit=10)
    assert len(events) == 1
    assert events[0]["user"] == "dm1"
    assert events[0]["action"] == "run_analysis"
    assert events[0]["payload"] == {"events": [{"airport": "HAN"}]}


def test_audit_event_filter_by_action(tmp_path) -> None:
    conn = _conn(tmp_path)
    record_audit_event(conn, user="dm1", action="run_analysis")
    record_audit_event(conn, user="dm1", action="settings_updated")
    record_audit_event(conn, user="dm1", action="run_analysis")
    only_runs = list_audit_events(conn, action="run_analysis")
    assert len(only_runs) == 2
    assert all(e["action"] == "run_analysis" for e in only_runs)


# ---------------------------------------------------------------------------
# settings
# ---------------------------------------------------------------------------


def test_get_settings_returns_defaults_when_unset(tmp_path) -> None:
    conn = _conn(tmp_path)
    s = get_settings(conn)
    assert s == DEFAULT_SETTINGS


def test_update_settings_persists_full_blob(tmp_path) -> None:
    conn = _conn(tmp_path)
    new_blob = {
        "load_factor": 0.7,
        "cost_per_pax_per_minute": 0.6,
        "seat_capacity": {"A321": 200},
        "level_delay_minutes": {"1": 200, "2": 100, "3": 60, "4": 30, "5": 15},
    }
    update_settings(conn, new_blob, updated_by="dm1")  # type: ignore[arg-type]
    loaded = get_settings(conn)
    assert loaded["load_factor"] == 0.7
    assert loaded["cost_per_pax_per_minute"] == 0.6
    assert loaded["seat_capacity"] == {"A321": 200}


def test_settings_to_estimator_kwargs_normalises_keys(tmp_path) -> None:
    conn = _conn(tmp_path)
    update_settings(
        conn,
        {
            "load_factor": 0.9,
            "cost_per_pax_per_minute": 0.4,
            "seat_capacity": {"a321": 200, "A350": 305},
            "level_delay_minutes": {"1": 240, "2": 120},
        },  # type: ignore[arg-type]
        updated_by="dm1",
    )
    s = get_settings(conn)
    kw = settings_to_estimator_kwargs(s)
    assert kw["load_factor"] == 0.9
    assert kw["seat_capacity"] == {"A321": 200, "A350": 305}
    assert kw["level_delay_minutes"] == {1: 240, 2: 120}
