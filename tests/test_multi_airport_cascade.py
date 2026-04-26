"""Multi-airport closure cascade tests."""

from datetime import date, time

import pandas as pd

from src.cascade.cascade_detector import detect_cascade, detect_cascade_multi
from src.models.event import AirportClosureEvent

D = date(2026, 4, 24)


def _evt(airport: str, t0: time = time(14, 0), t1: time = time(18, 0)) -> AirportClosureEvent:
    return AirportClosureEvent(
        airport=airport,
        closure_date=D,
        start_time=t0,
        end_time=t1,
    )


def _flight(
    no: str,
    reg: str,
    o: str,
    d: str,
    std: time,
    sta: time,
    ac_type: str = "A321",
) -> dict:
    return {
        "flight_no": no,
        "aircraft_reg": reg,
        "aircraft_type": ac_type,
        "origin": o,
        "destination": d,
        "std": std,
        "sta": sta,
        "flight_date": D,
    }


def test_single_event_via_multi_matches_single_api():
    """detect_cascade and detect_cascade_multi must agree on single-event input."""
    df = pd.DataFrame(
        [
            _flight(
                "VN1", "VN-A1", "SGN", "HAN", time(13, 0), time(15, 0)
            ),  # arrives during HAN closure
            _flight(
                "VN2", "VN-A1", "HAN", "SGN", time(16, 0), time(18, 30)
            ),  # departs from HAN during closure
            _flight("VN3", "VN-A1", "SGN", "DAD", time(20, 0), time(21, 30)),  # downstream
        ]
    )
    a = detect_cascade(df, _evt("HAN"))
    b = detect_cascade_multi(df, [_evt("HAN")])
    pd.testing.assert_series_equal(
        a["impact_level_numeric"].astype("object"),
        b["impact_level_numeric"].astype("object"),
        check_names=False,
    )


def test_multi_event_or_merge_flags_each_event_independently():
    """A flight hit by either of two simultaneous closures must be Level 1."""
    df = pd.DataFrame(
        [
            # Hit by HAN closure only
            _flight("VN1", "VN-A1", "SGN", "HAN", time(15, 0), time(17, 0)),
            # Hit by HPH closure only
            _flight("VN2", "VN-B1", "SGN", "HPH", time(15, 30), time(17, 30)),
            # Untouched by either
            _flight("VN3", "VN-C1", "SGN", "DAD", time(8, 0), time(9, 30)),
        ]
    )
    res = detect_cascade_multi(df, [_evt("HAN"), _evt("HPH")])
    rows = res.set_index("flight_no")
    assert rows.loc["VN1", "impact_level_numeric"] == 1
    assert rows.loc["VN2", "impact_level_numeric"] == 1
    assert rows.loc["VN3", "impact_level_numeric"] is None


def test_multi_event_cascade_propagates_through_combined_l1():
    """Pass 2 must run once on the union — a downstream flight after an L1
    triggered by event B should be cascade-flagged in the same chain as
    an L1 triggered by event A on the same aircraft."""
    df = pd.DataFrame(
        [
            # L1 from HAN closure
            _flight("VN10", "VN-A1", "HAN", "SGN", time(15, 0), time(17, 0)),
            # Downstream rotation, untouched directly
            _flight("VN11", "VN-A1", "SGN", "DAD", time(18, 30), time(20, 0)),
            # L1 from HPH closure (different aircraft)
            _flight("VN20", "VN-B1", "HPH", "SGN", time(16, 0), time(18, 0)),
            # Downstream rotation for B-aircraft
            _flight("VN21", "VN-B1", "SGN", "PXU", time(19, 0), time(20, 30)),
        ]
    )
    res = detect_cascade_multi(df, [_evt("HAN"), _evt("HPH")])
    rows = res.set_index("flight_no")
    # Both downstream flights should cascade off their respective L1s
    assert rows.loc["VN11", "impact_level_numeric"] == 2
    assert rows.loc["VN21", "impact_level_numeric"] == 2


def test_multi_event_empty_list_raises():
    df = pd.DataFrame([_flight("VN1", "VN-A1", "SGN", "HAN", time(15, 0), time(17, 0))])
    import pytest

    with pytest.raises(ValueError):
        detect_cascade_multi(df, [])
