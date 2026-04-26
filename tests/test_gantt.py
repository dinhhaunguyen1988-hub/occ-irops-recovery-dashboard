"""Tests for Plotly Gantt rotation chart builder."""

from datetime import date, time

import pandas as pd
import pytest

from src.models.event import AirportClosureEvent
from src.visualization.gantt import build_rotation_gantt

plotly = pytest.importorskip("plotly")  # noqa: F841


def _han_event() -> AirportClosureEvent:
    return AirportClosureEvent(
        airport="HAN",
        closure_date=date(2026, 4, 24),
        start_time=time(14, 0),
        end_time=time(18, 0),
    )


def _sample() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "flight_no": "VN1",
                "aircraft_reg": "VN-A500",
                "origin": "SGN",
                "destination": "HAN",
                "flight_date": date(2026, 4, 24),
                "std": time(13, 0),
                "sta": time(15, 0),
                "impact_level_display": "Level 1",
            },
            {
                "flight_no": "VN2",
                "aircraft_reg": "VN-A500",
                "origin": "HAN",
                "destination": "SGN",
                "flight_date": date(2026, 4, 24),
                "std": time(19, 0),
                "sta": time(20, 30),
                "impact_level_display": "Level 2",
            },
        ]
    )


def test_build_rotation_gantt_returns_figure():
    fig = build_rotation_gantt(_sample(), _han_event())
    assert fig is not None
    # Has at least one bar trace per impact level present
    assert len(fig.data) >= 1


def test_build_rotation_gantt_handles_empty_df():
    empty = pd.DataFrame(columns=["aircraft_reg"])
    assert build_rotation_gantt(empty, _han_event()) is None


def test_overnight_sector_extends_to_next_day():
    """STA earlier than STD should be interpreted as next-day arrival."""
    df = pd.DataFrame(
        [
            {
                "flight_no": "VN9",
                "aircraft_reg": "VN-X",
                "origin": "HAN",
                "destination": "ICN",
                "flight_date": date(2026, 4, 24),
                "std": time(23, 0),
                "sta": time(2, 0),  # next day
                "impact_level_display": "Level 1",
            }
        ]
    )
    fig = build_rotation_gantt(df, _han_event())
    assert fig is not None
