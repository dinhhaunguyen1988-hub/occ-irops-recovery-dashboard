"""Tests for multi-day / overnight cascade detection.

Validates:
- Pass 1 only marks Level 1 on the closure date even if data from D+1 is loaded.
- Pass 2 propagates the cascade onto the next day's flights for the same aircraft.
- Cascade depth is recorded on the Level 1 root flight.
"""

from datetime import date, time

import pandas as pd

from src.cascade.cascade_detector import detect_cascade
from src.models.event import AirportClosureEvent


def _han_event() -> AirportClosureEvent:
    return AirportClosureEvent(
        airport="HAN",
        closure_date=date(2026, 4, 24),
        start_time=time(14, 0),
        end_time=time(18, 0),
    )


def test_overnight_cascade_propagates_to_next_day():
    """A Level 1 on D should cascade to flights on D+1 for the same aircraft."""
    df = pd.DataFrame(
        [
            # Day D: Level 1 — arrives into closed HAN at 15:00
            {
                "flight_no": "VN201",
                "aircraft_reg": "VN-A500",
                "origin": "SGN",
                "destination": "HAN",
                "flight_date": date(2026, 4, 24),
                "std": time(13, 0),
                "sta": time(15, 0),
            },
            # Day D+1: should become Level 2 (downstream cascade)
            {
                "flight_no": "VN202",
                "aircraft_reg": "VN-A500",
                "origin": "HAN",
                "destination": "SGN",
                "flight_date": date(2026, 4, 25),
                "std": time(7, 0),
                "sta": time(8, 30),
            },
            # Day D+1: should become Level 3+
            {
                "flight_no": "VN203",
                "aircraft_reg": "VN-A500",
                "origin": "SGN",
                "destination": "DAD",
                "flight_date": date(2026, 4, 25),
                "std": time(10, 0),
                "sta": time(11, 0),
            },
        ]
    )

    result = detect_cascade(df, _han_event())

    levels = result.set_index("flight_no")["impact_level_numeric"].to_dict()
    assert levels["VN201"] == 1
    assert levels["VN202"] == 2
    assert levels["VN203"] == 3


def test_pass1_filters_by_closure_date():
    """A flight on D+1 arriving HAN at 15:00 must NOT be flagged Level 1."""
    df = pd.DataFrame(
        [
            {
                "flight_no": "VN300",
                "aircraft_reg": "VN-B100",
                "origin": "SGN",
                "destination": "HAN",
                "flight_date": date(2026, 4, 25),  # next day, not closure day
                "std": time(13, 0),
                "sta": time(15, 0),
            }
        ]
    )

    result = detect_cascade(df, _han_event())
    assert result.iloc[0]["impact_level_numeric"] is None


def test_cascade_depth_recorded_on_root():
    """Level 1 root flight gets cascade_depth = number of downstream sectors."""
    df = pd.DataFrame(
        [
            {
                "flight_no": "VN401",  # root, Level 1
                "aircraft_reg": "VN-C200",
                "origin": "DAD",
                "destination": "HAN",
                "flight_date": date(2026, 4, 24),
                "std": time(13, 0),
                "sta": time(15, 0),
            },
            {
                "flight_no": "VN402",
                "aircraft_reg": "VN-C200",
                "origin": "HAN",
                "destination": "DAD",
                "flight_date": date(2026, 4, 24),
                "std": time(19, 0),
                "sta": time(20, 30),
            },
            {
                "flight_no": "VN403",
                "aircraft_reg": "VN-C200",
                "origin": "DAD",
                "destination": "SGN",
                "flight_date": date(2026, 4, 25),
                "std": time(7, 0),
                "sta": time(8, 30),
            },
        ]
    )

    result = detect_cascade(df, _han_event())
    by_flt = result.set_index("flight_no")
    assert by_flt.at["VN401", "cascade_depth"] == 2
    assert by_flt.at["VN402", "cascade_depth"] == 0
    assert by_flt.at["VN403", "cascade_depth"] == 0
