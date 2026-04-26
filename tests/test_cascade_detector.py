"""Tests for cascade detection logic."""

from datetime import date, time

import pandas as pd
import pytest

from src.cascade.cascade_detector import compute_kpis, detect_cascade, display_impact_level
from src.models.event import AirportClosureEvent


@pytest.fixture
def han_closure():
    """Standard HAN closure event for testing."""
    return AirportClosureEvent(
        airport="HAN",
        closure_date=date(2026, 4, 24),
        start_time=time(14, 0),
        end_time=time(18, 0),
    )


def _make_flight_df(flights: list[dict]) -> pd.DataFrame:
    """Create a flight DataFrame from a list of flight dictionaries."""
    return pd.DataFrame(flights)


class TestDisplayImpactLevel:
    def test_none(self):
        assert display_impact_level(None) == "Not affected"

    def test_level_1(self):
        assert display_impact_level(1) == "Level 1"

    def test_level_2(self):
        assert display_impact_level(2) == "Level 2"

    def test_level_3(self):
        assert display_impact_level(3) == "3+"

    def test_level_4(self):
        assert display_impact_level(4) == "3+"

    def test_level_5(self):
        assert display_impact_level(5) == "3+"


class TestBoundaryConditions:
    def test_arrival_before_closure(self, han_closure):
        df = _make_flight_df(
            [
                {
                    "flight_no": "A",
                    "aircraft_reg": "VN-A100",
                    "origin": "DAD",
                    "destination": "HAN",
                    "std": time(11, 0),
                    "sta": time(13, 59),
                }
            ]
        )
        result = detect_cascade(df, han_closure)
        assert result.iloc[0]["impact_level_numeric"] is None

    def test_arrival_at_closure_start_inclusive(self, han_closure):
        df = _make_flight_df(
            [
                {
                    "flight_no": "B",
                    "aircraft_reg": "VN-A100",
                    "origin": "DAD",
                    "destination": "HAN",
                    "std": time(12, 40),
                    "sta": time(14, 0),
                }
            ]
        )
        result = detect_cascade(df, han_closure)
        assert result.iloc[0]["impact_level_numeric"] == 1

    def test_arrival_within_closure(self, han_closure):
        df = _make_flight_df(
            [
                {
                    "flight_no": "C",
                    "aircraft_reg": "VN-A100",
                    "origin": "DAD",
                    "destination": "HAN",
                    "std": time(12, 40),
                    "sta": time(17, 59),
                }
            ]
        )
        result = detect_cascade(df, han_closure)
        assert result.iloc[0]["impact_level_numeric"] == 1

    def test_arrival_at_closure_end_exclusive(self, han_closure):
        df = _make_flight_df(
            [
                {
                    "flight_no": "D",
                    "aircraft_reg": "VN-A100",
                    "origin": "DAD",
                    "destination": "HAN",
                    "std": time(12, 40),
                    "sta": time(18, 0),
                }
            ]
        )
        result = detect_cascade(df, han_closure)
        assert result.iloc[0]["impact_level_numeric"] is None

    def test_departure_from_closed_airport(self, han_closure):
        df = _make_flight_df(
            [
                {
                    "flight_no": "E",
                    "aircraft_reg": "VN-A100",
                    "origin": "HAN",
                    "destination": "DAD",
                    "std": time(14, 35),
                    "sta": time(15, 55),
                }
            ]
        )
        result = detect_cascade(df, han_closure)
        assert result.iloc[0]["impact_level_numeric"] == 1

    def test_departure_at_closure_end_not_affected(self, han_closure):
        df = _make_flight_df(
            [
                {
                    "flight_no": "F",
                    "aircraft_reg": "VN-A100",
                    "origin": "HAN",
                    "destination": "DAD",
                    "std": time(18, 0),
                    "sta": time(19, 20),
                }
            ]
        )
        result = detect_cascade(df, han_closure)
        assert result.iloc[0]["impact_level_numeric"] is None


class TestMultipleLevel1SameAircraft:
    def test_standard_cascade_scenario(self, han_closure):
        """Test the standard scenario from the spec:
        1504: DAD->HAN arr 14:00 => Level 1
        1505: HAN->DAD dep 14:35 => Level 1
        637:  DAD->SGN dep 16:40 => Level 2 (downstream)
        1801: SGN->BLR dep 19:20 => Level 3+ (extended downstream)
        """
        flights = [
            {
                "flight_no": "1504",
                "aircraft_reg": "VN-A500",
                "origin": "DAD",
                "destination": "HAN",
                "std": time(12, 40),
                "sta": time(14, 0),
            },
            {
                "flight_no": "1505",
                "aircraft_reg": "VN-A500",
                "origin": "HAN",
                "destination": "DAD",
                "std": time(14, 35),
                "sta": time(15, 55),
            },
            {
                "flight_no": "637",
                "aircraft_reg": "VN-A500",
                "origin": "DAD",
                "destination": "SGN",
                "std": time(16, 40),
                "sta": time(18, 0),
            },
            {
                "flight_no": "1801",
                "aircraft_reg": "VN-A500",
                "origin": "SGN",
                "destination": "BLR",
                "std": time(19, 20),
                "sta": time(22, 35),
            },
        ]
        df = _make_flight_df(flights)
        result = detect_cascade(df, han_closure)

        assert result.iloc[0]["impact_level_numeric"] == 1
        assert result.iloc[1]["impact_level_numeric"] == 1
        assert result.iloc[2]["impact_level_numeric"] == 2
        assert result.iloc[3]["impact_level_numeric"] == 3

        assert result.iloc[0]["impact_level_display"] == "Level 1"
        assert result.iloc[1]["impact_level_display"] == "Level 1"
        assert result.iloc[2]["impact_level_display"] == "Level 2"
        assert result.iloc[3]["impact_level_display"] == "3+"


class TestNonAffectedAircraft:
    def test_unrelated_aircraft(self, han_closure):
        flights = [
            {
                "flight_no": "100",
                "aircraft_reg": "VN-B200",
                "origin": "SGN",
                "destination": "DAD",
                "std": time(8, 0),
                "sta": time(9, 30),
            },
            {
                "flight_no": "101",
                "aircraft_reg": "VN-B200",
                "origin": "DAD",
                "destination": "SGN",
                "std": time(10, 0),
                "sta": time(11, 30),
            },
        ]
        df = _make_flight_df(flights)
        result = detect_cascade(df, han_closure)

        assert result.iloc[0]["impact_level_numeric"] is None
        assert result.iloc[1]["impact_level_numeric"] is None


class TestAuditReasons:
    def test_arrival_reason(self, han_closure):
        df = _make_flight_df(
            [
                {
                    "flight_no": "1504",
                    "aircraft_reg": "VN-A500",
                    "origin": "DAD",
                    "destination": "HAN",
                    "std": time(12, 40),
                    "sta": time(14, 0),
                }
            ]
        )
        result = detect_cascade(df, han_closure)
        assert "Arrival into closed airport" in result.iloc[0]["impact_reason"]

    def test_departure_reason(self, han_closure):
        df = _make_flight_df(
            [
                {
                    "flight_no": "1505",
                    "aircraft_reg": "VN-A500",
                    "origin": "HAN",
                    "destination": "DAD",
                    "std": time(14, 35),
                    "sta": time(15, 55),
                }
            ]
        )
        result = detect_cascade(df, han_closure)
        assert "Departure from closed airport" in result.iloc[0]["impact_reason"]

    def test_downstream_reason(self, han_closure):
        flights = [
            {
                "flight_no": "1504",
                "aircraft_reg": "VN-A500",
                "origin": "DAD",
                "destination": "HAN",
                "std": time(12, 40),
                "sta": time(14, 0),
            },
            {
                "flight_no": "637",
                "aircraft_reg": "VN-A500",
                "origin": "DAD",
                "destination": "SGN",
                "std": time(16, 40),
                "sta": time(18, 0),
            },
        ]
        df = _make_flight_df(flights)
        result = detect_cascade(df, han_closure)
        assert "Downstream" in result.iloc[1]["impact_reason"]


class TestComputeKpis:
    def test_kpi_counts(self, han_closure):
        flights = [
            {
                "flight_no": "1504",
                "aircraft_reg": "VN-A500",
                "origin": "DAD",
                "destination": "HAN",
                "std": time(12, 40),
                "sta": time(14, 0),
            },
            {
                "flight_no": "1505",
                "aircraft_reg": "VN-A500",
                "origin": "HAN",
                "destination": "DAD",
                "std": time(14, 35),
                "sta": time(15, 55),
            },
            {
                "flight_no": "637",
                "aircraft_reg": "VN-A500",
                "origin": "DAD",
                "destination": "SGN",
                "std": time(16, 40),
                "sta": time(18, 0),
            },
            {
                "flight_no": "1801",
                "aircraft_reg": "VN-A500",
                "origin": "SGN",
                "destination": "BLR",
                "std": time(19, 20),
                "sta": time(22, 35),
            },
            {
                "flight_no": "100",
                "aircraft_reg": "VN-B200",
                "origin": "SGN",
                "destination": "DAD",
                "std": time(8, 0),
                "sta": time(9, 30),
            },
        ]
        df = _make_flight_df(flights)
        result = detect_cascade(df, han_closure)
        kpis = compute_kpis(result)

        assert kpis["total_flights"] == 5
        assert kpis["affected_flights"] == 4
        assert kpis["level_1_count"] == 2
        assert kpis["level_2_count"] == 1
        assert kpis["level_3plus_count"] == 1
        assert kpis["aircraft_affected"] == 1
