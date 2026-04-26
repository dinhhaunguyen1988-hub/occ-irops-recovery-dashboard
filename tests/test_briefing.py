"""Tests for the briefing payload builder."""

from __future__ import annotations

from src.integration.briefing import build_briefing_payload


def test_empty_runs_renders_no_runs_message() -> None:
    out = build_briefing_payload([])
    assert "no runs" in out.subject.lower()
    assert "No cascade analysis runs" in out.text_body
    assert "<h2>" in out.html_body


def test_briefing_subject_lists_run_count() -> None:
    runs = [
        {
            "id": 1,
            "created_at": "2026-04-25 06:00:00",
            "closure_config": [],
            "kpi_snapshot": {},
        }
    ]
    out = build_briefing_payload(runs)
    assert "1 run" in out.subject


def test_briefing_text_body_includes_kpi_summary_per_run() -> None:
    runs = [
        {
            "id": 7,
            "created_at": "2026-04-25 06:00:00",
            "closure_config": [{"airport": "HAN", "start_time": "14:00", "end_time": "18:00"}],
            "kpi_snapshot": {
                "level_1_count": 51,
                "level_2_count": 41,
                "level_3plus_count": 47,
                "total_pax_disrupted": 27827,
                "total_cost_usd": 1898730.0,
            },
        }
    ]
    out = build_briefing_payload(runs)
    assert "#7" in out.text_body
    assert "HAN 14:00-18:00" in out.text_body
    assert "L1=51" in out.text_body
    assert "27827" in out.text_body
    assert "<table" in out.html_body
    # HTML escaping of $ is fine; just check the cost number is present.
    assert "1898730" in out.html_body


def test_briefing_handles_runs_with_missing_fields() -> None:
    runs = [{"id": 1}]
    out = build_briefing_payload(runs)  # must not raise
    assert "1 run" in out.subject
