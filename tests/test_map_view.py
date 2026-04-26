"""Tests for src.visualization.map_view + airport_coords."""

from datetime import date, time

import pandas as pd

from src.models.event import AirportClosureEvent
from src.visualization.airport_coords import AIRPORT_COORDS, get_coords
from src.visualization.map_view import build_airport_map


def test_known_airport_returns_coords():
    coords = get_coords("HAN")
    assert coords is not None
    lat, lon = coords
    # Roughly Hanoi airport
    assert 20 < lat < 22
    assert 105 < lon < 107


def test_unknown_airport_returns_none():
    assert get_coords("ZZZ") is None
    assert get_coords("") is None
    assert get_coords(None) is None


def test_known_airports_table_size():
    """Sanity: at least 10 airports configured."""
    assert len(AIRPORT_COORDS) >= 10


def _evt() -> AirportClosureEvent:
    return AirportClosureEvent(
        airport="HAN",
        closure_date=date(2026, 4, 24),
        start_time=time(14, 0),
        end_time=time(18, 0),
    )


def _df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "flight_no": "VN1",
                "aircraft_reg": "VN-A1",
                "origin": "SGN",
                "destination": "HAN",
                "std": time(15, 0),
                "sta": time(17, 0),
                "flight_date": date(2026, 4, 24),
                "impact_level_numeric": 1,
            },
            {
                "flight_no": "VN2",
                "aircraft_reg": "VN-A1",
                "origin": "HAN",
                "destination": "DAD",
                "std": time(18, 30),
                "sta": time(19, 45),
                "flight_date": date(2026, 4, 24),
                "impact_level_numeric": 2,
            },
        ]
    )


def test_build_map_returns_figure_with_traces():
    plotly = pytest_importorskip("plotly")  # type: ignore  # noqa: F841
    fig = build_airport_map(_df(), [_evt()])
    assert fig is not None
    # At least one trace (closed) and likely a couple more
    assert len(fig.data) >= 1


def test_build_map_returns_none_when_no_known_airports():
    df = pd.DataFrame(
        [
            {
                "flight_no": "X",
                "origin": "ZZZ",
                "destination": "QQQ",
                "std": time(10, 0),
                "sta": time(11, 0),
                "flight_date": date(2026, 4, 24),
                "impact_level_numeric": None,
            }
        ]
    )
    ev = AirportClosureEvent(
        airport="ZZZ",
        closure_date=date(2026, 4, 24),
        start_time=time(14, 0),
        end_time=time(18, 0),
    )
    fig = build_airport_map(df, [ev])
    assert fig is None


# pytest helper accessor
def pytest_importorskip(name: str):
    import pytest

    return pytest.importorskip(name)
