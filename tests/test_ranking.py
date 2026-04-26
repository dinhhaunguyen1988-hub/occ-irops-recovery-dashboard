"""Tests for priority ranking."""

import pandas as pd

from src.cascade.ranking import compute_priority


def test_level_1_higher_than_level_2_higher_than_level_3():
    df = pd.DataFrame(
        [
            {
                "flight_no": "A",
                "impact_level_numeric": 1,
                "cascade_depth": 0,
                "origin": "HAN",
                "destination": "SGN",
            },
            {
                "flight_no": "B",
                "impact_level_numeric": 2,
                "cascade_depth": 0,
                "origin": "HAN",
                "destination": "SGN",
            },
            {
                "flight_no": "C",
                "impact_level_numeric": 3,
                "cascade_depth": 0,
                "origin": "HAN",
                "destination": "SGN",
            },
            {
                "flight_no": "D",
                "impact_level_numeric": None,
                "cascade_depth": 0,
                "origin": "HAN",
                "destination": "SGN",
            },
        ]
    )

    out = compute_priority(df)
    scores = dict(zip(out["flight_no"], out["priority_score"], strict=False))
    assert scores["A"] > scores["B"] > scores["C"] > scores["D"]
    assert scores["D"] == 0


def test_cascade_depth_boosts_level_1_score():
    df = pd.DataFrame(
        [
            {
                "flight_no": "shallow",
                "impact_level_numeric": 1,
                "cascade_depth": 0,
                "origin": "HAN",
                "destination": "SGN",
            },
            {
                "flight_no": "deep",
                "impact_level_numeric": 1,
                "cascade_depth": 5,
                "origin": "HAN",
                "destination": "SGN",
            },
        ]
    )
    out = compute_priority(df)
    by = dict(zip(out["flight_no"], out["priority_score"], strict=False))
    assert by["deep"] - by["shallow"] == 50  # 5 * 10


def test_international_route_adds_bonus():
    df = pd.DataFrame(
        [
            {
                "flight_no": "DOM",
                "impact_level_numeric": 1,
                "cascade_depth": 0,
                "origin": "HAN",
                "destination": "SGN",
            },
            {
                "flight_no": "INT",
                "impact_level_numeric": 1,
                "cascade_depth": 0,
                "origin": "HAN",
                "destination": "ICN",
            },
        ]
    )
    out = compute_priority(df)
    by = dict(zip(out["flight_no"], out["priority_score"], strict=False))
    assert by["INT"] - by["DOM"] == 20
