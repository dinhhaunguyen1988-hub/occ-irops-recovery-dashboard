"""Tests for src.impact.pax_estimator."""

from datetime import date, time

import pandas as pd

from src.impact.pax_estimator import (
    DEFAULT_LOAD_FACTOR,
    DEFAULT_SEAT_CAPACITY,
    LEVEL_DELAY_MINUTES,
    estimate_pax_and_cost,
)


def _row(ac_type: str, level: object) -> dict:
    return {
        "flight_no": f"VN-{ac_type}",
        "aircraft_type": ac_type,
        "origin": "SGN",
        "destination": "HAN",
        "std": time(10, 0),
        "sta": time(12, 0),
        "flight_date": date(2026, 4, 24),
        "impact_level_numeric": level,
    }


def test_pax_uses_capacity_table_and_load_factor():
    df = pd.DataFrame([_row("A321", 1)])
    out = estimate_pax_and_cost(df)
    expected_pax = round(DEFAULT_SEAT_CAPACITY["A321"] * DEFAULT_LOAD_FACTOR)
    assert int(out["est_pax"].iloc[0]) == expected_pax


def test_unknown_aircraft_type_yields_zero_pax():
    df = pd.DataFrame([_row("ZZ999", 1)])
    out = estimate_pax_and_cost(df)
    assert int(out["est_pax"].iloc[0]) == 0
    assert float(out["est_cost_usd"].iloc[0]) == 0.0


def test_aircraft_type_prefix_match():
    """A321NEO should still resolve to A321 capacity via prefix match."""
    df = pd.DataFrame([_row("A321NEO", 1)])
    out = estimate_pax_and_cost(df)
    assert int(out["est_pax"].iloc[0]) > 0


def test_delay_minutes_tracks_impact_level():
    df = pd.DataFrame(
        [
            _row("A321", 1),
            _row("A321", 2),
            _row("A321", 3),
            _row("A321", None),
        ]
    )
    out = estimate_pax_and_cost(df)
    assert int(out["est_delay_minutes"].iloc[0]) == LEVEL_DELAY_MINUTES[1]
    assert int(out["est_delay_minutes"].iloc[1]) == LEVEL_DELAY_MINUTES[2]
    assert int(out["est_delay_minutes"].iloc[2]) == LEVEL_DELAY_MINUTES[3]
    # Unaffected flights have zero delay → zero cost
    assert int(out["est_delay_minutes"].iloc[3]) == 0
    assert float(out["est_cost_usd"].iloc[3]) == 0.0


def test_cost_overrides_propagate():
    """Overriding cost_per_pax_per_minute scales est_cost_usd linearly."""
    df = pd.DataFrame([_row("A321", 1)])
    base = estimate_pax_and_cost(df, cost_per_pax_per_minute=0.50)
    high = estimate_pax_and_cost(df, cost_per_pax_per_minute=1.00)
    assert float(high["est_cost_usd"].iloc[0]) == float(base["est_cost_usd"].iloc[0]) * 2


def test_seat_capacity_override():
    """Custom seat capacity table overrides defaults."""
    df = pd.DataFrame([_row("CUSTOM", 1)])
    out = estimate_pax_and_cost(df, seat_capacity={"CUSTOM": 100})
    expected_pax = round(100 * DEFAULT_LOAD_FACTOR)
    assert int(out["est_pax"].iloc[0]) == expected_pax
