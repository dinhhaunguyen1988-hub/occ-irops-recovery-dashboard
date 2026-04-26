"""Tests for the multi-day stress test."""

from __future__ import annotations

from datetime import date, time

import pandas as pd

from src.decision.stress import StressScenario, run_stress_test
from src.parser.dayrep_parser import parse_dayrep_report

SAMPLE = "data/sample/sample_dayrep_24042026.xlsx"


def test_zero_duration_returns_empty() -> None:
    df = pd.DataFrame({"flight_no": ["VN1"], "flight_date": [date(2026, 4, 24)]})
    res = run_stress_test(
        df,
        StressScenario(
            airports=("HAN",),
            start_date=date(2026, 4, 24),
            duration_days=0,
            closure_start=time(14, 0),
            closure_end=time(18, 0),
        ),
    )
    assert res.per_day == []
    assert res.worst_day is None


def test_empty_dataframe_returns_empty() -> None:
    res = run_stress_test(
        pd.DataFrame(),
        StressScenario(
            airports=("HAN",),
            start_date=date(2026, 4, 24),
            duration_days=3,
            closure_start=time(14, 0),
            closure_end=time(18, 0),
        ),
    )
    assert res.per_day == []


def test_three_day_scenario_produces_three_per_day_entries() -> None:
    import os

    if not os.path.exists(SAMPLE):
        return
    df, _ = parse_dayrep_report(SAMPLE)
    res = run_stress_test(
        df,
        StressScenario(
            airports=("HAN",),
            start_date=date(2026, 4, 24),
            duration_days=3,
            closure_start=time(14, 0),
            closure_end=time(18, 0),
        ),
    )
    assert len(res.per_day) == 3
    assert res.worst_day is not None
    # Totals should equal 3 × per-day (since same schedule replayed each day).
    assert res.totals["affected_flights"] == sum(
        int(d.get("affected_flights", 0)) for d in res.per_day
    )


def test_multi_airport_scenario_runs_without_error() -> None:
    import os

    if not os.path.exists(SAMPLE):
        return
    df, _ = parse_dayrep_report(SAMPLE)
    res = run_stress_test(
        df,
        StressScenario(
            airports=("HAN", "HPH"),
            start_date=date(2026, 4, 24),
            duration_days=2,
            closure_start=time(14, 0),
            closure_end=time(18, 0),
        ),
    )
    assert len(res.per_day) == 2
    assert res.totals["affected_flights"] > 0


def test_multi_day_aggregate_totals_are_consistent() -> None:
    import os

    if not os.path.exists(SAMPLE):
        return
    df, _ = parse_dayrep_report(SAMPLE)
    res = run_stress_test(
        df,
        StressScenario(
            airports=("HAN",),
            start_date=date(2026, 4, 24),
            duration_days=2,
            closure_start=time(14, 0),
            closure_end=time(18, 0),
        ),
    )
    # Worst-day cost ≤ total cost (worst day is one of the days).
    assert res.worst_day is not None
    assert float(res.worst_day["total_cost_usd"]) <= res.totals["total_cost_usd"]
