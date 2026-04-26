"""Tests for the pax reaccommodation list builder."""

from __future__ import annotations

import pandas as pd

from src.decision.reaccommodation import build_reaccommodation_list


def _make_df(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    if "impact_level_numeric" not in df.columns:
        df["impact_level_numeric"] = None
    if "cascade_depth" not in df.columns:
        df["cascade_depth"] = 0
    if "est_pax" not in df.columns:
        df["est_pax"] = 0
    return df


def test_empty_dataframe_returns_empty_list() -> None:
    assert build_reaccommodation_list(pd.DataFrame()) == []


def test_unaffected_flights_are_excluded() -> None:
    df = _make_df(
        [
            {
                "flight_no": "VN1",
                "origin": "HAN",
                "destination": "SGN",
                "impact_level_numeric": None,
                "est_pax": 180,
            },
        ]
    )
    assert build_reaccommodation_list(df) == []


def test_international_outranks_domestic() -> None:
    df = _make_df(
        [
            {
                "flight_no": "VN-DOM",
                "aircraft_reg": "VN-A001",
                "origin": "HAN",
                "destination": "SGN",
                "impact_level_numeric": 1,
                "est_pax": 200,
            },
            {
                "flight_no": "VN-INTL",
                "aircraft_reg": "VN-B002",
                "origin": "HAN",
                "destination": "ICN",
                "impact_level_numeric": 1,
                "est_pax": 150,
            },
        ]
    )
    rows = build_reaccommodation_list(df)
    assert rows[0].flight_no == "VN-INTL"
    assert rows[0].is_international is True
    assert rows[1].flight_no == "VN-DOM"


def test_higher_pax_outranks_lower_within_same_intl_class() -> None:
    df = _make_df(
        [
            {
                "flight_no": "VN-LOW",
                "origin": "HAN",
                "destination": "SGN",
                "impact_level_numeric": 1,
                "est_pax": 100,
            },
            {
                "flight_no": "VN-HIGH",
                "origin": "HAN",
                "destination": "SGN",
                "impact_level_numeric": 1,
                "est_pax": 290,
            },
        ]
    )
    rows = build_reaccommodation_list(df)
    assert rows[0].flight_no == "VN-HIGH"


def test_rationale_mentions_intl_and_high_pax_load() -> None:
    df = _make_df(
        [
            {
                "flight_no": "VN54",
                "origin": "HAN",
                "destination": "FRA",
                "impact_level_numeric": 1,
                "est_pax": 290,
                "cascade_depth": 3,
            },
        ]
    )
    rows = build_reaccommodation_list(df)
    assert "International" in rows[0].rationale
    assert "High pax" in rows[0].rationale
    assert "Cascade depth 3" in rows[0].rationale


def test_only_levels_filter() -> None:
    df = _make_df(
        [
            {
                "flight_no": "VN-L1",
                "origin": "HAN",
                "destination": "SGN",
                "impact_level_numeric": 1,
                "est_pax": 100,
            },
            {
                "flight_no": "VN-L2",
                "origin": "HAN",
                "destination": "SGN",
                "impact_level_numeric": 2,
                "est_pax": 100,
            },
        ]
    )
    rows = build_reaccommodation_list(df, only_levels=(1,))
    assert len(rows) == 1
    assert rows[0].flight_no == "VN-L1"


def test_rank_starts_at_one_and_is_contiguous() -> None:
    df = _make_df(
        [
            {
                "flight_no": f"VN{i}",
                "origin": "HAN",
                "destination": "SGN",
                "impact_level_numeric": 1,
                "est_pax": 100 + i,
            }
            for i in range(5)
        ]
    )
    rows = build_reaccommodation_list(df)
    assert [r.rank for r in rows] == [1, 2, 3, 4, 5]
