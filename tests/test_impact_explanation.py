"""Discrepancy explainer tests (Sprint 4).

Verifies that ``impact_explanation`` is populated with concrete, useful
text that DMs can use to argue classifications with crew/control.
"""

from __future__ import annotations

from datetime import date, time

import pandas as pd

from src.cascade.cascade_detector import detect_cascade_multi
from src.models.event import AirportClosureEvent


def _build_simple_fleet() -> pd.DataFrame:
    """Two tails. VN-A517 hits HAN closure (L1) then continues SGN later (L2).

    VN101: SGN \u2192 HAN STA 15:00 \u2192 L1 (arrives during closure)
    VN102: HAN \u2192 SGN STD 19:00 \u2192 L2 (rotation after L1, outside closure)
    VN201/VN202: SGN \u2194 DAD only, never touches HAN \u2192 unaffected.
    """
    return pd.DataFrame(
        {
            "flight_date": [date(2026, 4, 24)] * 4,
            "flight_no": ["VN101", "VN102", "VN201", "VN202"],
            "aircraft_reg": ["VN-A517", "VN-A517", "VN-A518", "VN-A518"],
            "aircraft_type": ["A321"] * 4,
            "origin": ["SGN", "HAN", "SGN", "DAD"],
            "destination": ["HAN", "SGN", "DAD", "SGN"],
            "std": [time(13, 0), time(19, 0), time(8, 0), time(12, 0)],
            "sta": [time(15, 0), time(21, 0), time(10, 0), time(14, 0)],
        }
    )


def _han_event() -> AirportClosureEvent:
    return AirportClosureEvent(
        airport="HAN",
        closure_date=date(2026, 4, 24),
        start_time=time(14, 0),
        end_time=time(18, 0),
        closure_type="airport_closed",
    )


def test_level1_explanation_mentions_airport_window_and_time() -> None:
    df = detect_cascade_multi(_build_simple_fleet(), [_han_event()])
    l1 = df[df["impact_level_numeric"] == 1].iloc[0]
    expl = l1["impact_explanation"]
    assert "HAN" in expl
    assert "14:00" in expl and "18:00" in expl
    assert "2026-04-24" in expl
    assert "airport closed" in expl


def test_level1_explanation_includes_scheduled_time() -> None:
    df = detect_cascade_multi(_build_simple_fleet(), [_han_event()])
    l1 = df[df["flight_no"] == "VN101"].iloc[0]
    assert l1["impact_level_numeric"] == 1
    # VN101 arrives HAN at 15:00, inside the 14:00–18:00 window.
    assert "STA 15:00" in l1["impact_explanation"]
    assert "arrives at HAN" in l1["impact_explanation"]


def test_level2_explanation_names_root_flight_and_tail() -> None:
    df = detect_cascade_multi(_build_simple_fleet(), [_han_event()])
    l2_rows = df[df["impact_level_numeric"] == 2]
    assert not l2_rows.empty
    expl = l2_rows.iloc[0]["impact_explanation"]
    assert "VN-A517" in expl
    # Root must be one of the L1 flight numbers we constructed
    assert any(fn in expl for fn in ("VN101", "VN102"))
    assert "hop 1" in expl


def test_unaffected_flight_has_empty_explanation() -> None:
    df = detect_cascade_multi(_build_simple_fleet(), [_han_event()])
    not_affected = df[df["impact_level_numeric"].isna()]
    if not not_affected.empty:
        assert (not_affected["impact_explanation"].astype(str) == "").all()


def test_multi_event_explanation_lists_all_triggering_events() -> None:
    """A flight matched by two simultaneous events must mention both."""
    df = pd.DataFrame(
        {
            "flight_date": [date(2026, 4, 24)],
            "flight_no": ["VN999"],
            "aircraft_reg": ["VN-A999"],
            "aircraft_type": ["A350"],
            "origin": ["HAN"],
            "destination": ["HPH"],
            "std": [time(15, 0)],
            "sta": [time(15, 30)],
        }
    )
    events = [
        AirportClosureEvent(
            airport="HAN",
            closure_date=date(2026, 4, 24),
            start_time=time(14, 0),
            end_time=time(18, 0),
            closure_type="airport_closed",
        ),
        AirportClosureEvent(
            airport="HPH",
            closure_date=date(2026, 4, 24),
            start_time=time(14, 0),
            end_time=time(18, 0),
            closure_type="atc_flow",
        ),
    ]
    out = detect_cascade_multi(df, events)
    expl = out.iloc[0]["impact_explanation"]
    assert "HAN" in expl and "HPH" in expl
    assert "airport closed" in expl
    assert "atc flow" in expl
