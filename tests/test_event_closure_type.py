"""Tests for the closure_type field on AirportClosureEvent."""

from datetime import date, time

import pytest

from src.models.event import CLOSURE_TYPES, AirportClosureEvent


def test_default_closure_type_is_airport_closed():
    ev = AirportClosureEvent(
        airport="HAN",
        closure_date=date(2026, 4, 24),
        start_time=time(14, 0),
        end_time=time(18, 0),
    )
    assert ev.closure_type == "airport_closed"
    assert ev.closure_type_label == "Airport closed"
    # Colour from taxonomy table (red)
    assert ev.closure_type_colour == CLOSURE_TYPES["airport_closed"]["colour"]


@pytest.mark.parametrize("ctype", ["airport_closed", "runway_closed", "atc_flow"])
def test_each_known_closure_type_round_trips(ctype: str):
    ev = AirportClosureEvent(
        airport="DAD",
        closure_date=date(2026, 4, 24),
        start_time=time(8, 0),
        end_time=time(10, 0),
        closure_type=ctype,
    )
    assert ev.closure_type == ctype
    assert ev.closure_type_label == CLOSURE_TYPES[ctype]["label"]
    assert ev.closure_type_colour.startswith("#")


def test_unknown_closure_type_rejected():
    with pytest.raises(ValueError, match="Unknown closure_type"):
        AirportClosureEvent(
            airport="HAN",
            closure_date=date(2026, 4, 24),
            start_time=time(14, 0),
            end_time=time(18, 0),
            closure_type="volcano",
        )


def test_str_includes_type_label():
    ev = AirportClosureEvent(
        airport="HPH",
        closure_date=date(2026, 4, 24),
        start_time=time(14, 0),
        end_time=time(18, 0),
        closure_type="runway_closed",
    )
    assert "runway closed" in str(ev).lower()
    assert "HPH" in str(ev)
