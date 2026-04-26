"""Tests for the recovery suggestion engine."""

from __future__ import annotations

import pandas as pd
import pytest

from src.decision.recovery import (
    DEFAULT_WEIGHTS,
    RecoveryOption,
    score_options,
    suggest_recovery_options,
)


def _make_df(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    if "impact_level_numeric" not in df.columns:
        df["impact_level_numeric"] = None
    if "cascade_depth" not in df.columns:
        df["cascade_depth"] = 0
    if "est_pax" not in df.columns:
        df["est_pax"] = 0
    if "est_cost_usd" not in df.columns:
        df["est_cost_usd"] = 0.0
    return df


# ---------------------------------------------------------------------------
# Fan-out
# ---------------------------------------------------------------------------


def test_no_l1_returns_empty() -> None:
    df = _make_df(
        [
            {
                "flight_no": "VN100",
                "aircraft_reg": "VN-A001",
                "impact_level_numeric": 2,
                "est_pax": 180,
                "est_cost_usd": 5000.0,
            },
        ]
    )
    assert suggest_recovery_options(df) == []


def test_each_l1_gets_three_options_when_swap_available() -> None:
    df = _make_df(
        [
            {
                "flight_no": "VN100",
                "aircraft_reg": "VN-A001",
                "impact_level_numeric": 1,
                "est_pax": 180,
                "est_cost_usd": 5000.0,
            },
            {
                "flight_no": "VN200",
                "aircraft_reg": "VN-B002",
                "impact_level_numeric": None,
                "est_pax": 0,
                "est_cost_usd": 0.0,
            },
        ]
    )
    opts = suggest_recovery_options(df)
    options_for_vn100 = [o for o in opts if o.flight_no == "VN100"]
    types = {o.option for o in options_for_vn100}
    assert types == {"delay", "swap_tail", "cancel"}


def test_no_swap_when_no_free_tails() -> None:
    df = _make_df(
        [
            {
                "flight_no": "VN100",
                "aircraft_reg": "VN-A001",
                "impact_level_numeric": 1,
                "est_pax": 180,
                "est_cost_usd": 5000.0,
            },
        ]
    )
    opts = suggest_recovery_options(df)
    types = {o.option for o in opts}
    assert types == {"delay", "cancel"}


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------


def test_swap_beats_delay_beats_cancel_when_pax_high() -> None:
    """With pax weight dominant, swap (0 pax) < delay (180) < cancel (180 + extra)."""
    opts = [
        RecoveryOption(
            flight_no="A",
            aircraft_reg="VN-A001",
            option="delay",
            description="",
            pax_affected=180,
            cost_usd=5000.0,
        ),
        RecoveryOption(
            flight_no="A",
            aircraft_reg="VN-A001",
            option="swap_tail",
            description="",
            pax_affected=0,
            cost_usd=500.0,
        ),
        RecoveryOption(
            flight_no="A",
            aircraft_reg="VN-A001",
            option="cancel",
            description="",
            pax_affected=180,
            cost_usd=7500.0,
        ),
    ]
    sorted_opts = score_options(opts, weights={"pax": 1.0, "cost": 0.0, "op": 50.0})
    # swap has op=1×50=50; delay has 180+0=180; cancel has 180+150=330
    assert [o.option for o in sorted_opts] == ["swap_tail", "delay", "cancel"]


def test_score_is_set_in_place() -> None:
    opts = [
        RecoveryOption(
            flight_no="A",
            aircraft_reg=None,
            option="delay",
            description="",
            pax_affected=10,
            cost_usd=100.0,
        ),
    ]
    score_options(opts)
    assert opts[0].score == pytest.approx(
        DEFAULT_WEIGHTS["pax"] * 10 + DEFAULT_WEIGHTS["cost"] * 100.0 + DEFAULT_WEIGHTS["op"] * 0.0
    )


def test_options_grouped_by_flight_after_sort() -> None:
    """When two flights are present, options are grouped by flight_no."""
    df = _make_df(
        [
            {
                "flight_no": "VN100",
                "aircraft_reg": "VN-A001",
                "impact_level_numeric": 1,
                "est_pax": 180,
                "est_cost_usd": 5000.0,
            },
            {
                "flight_no": "VN200",
                "aircraft_reg": "VN-A002",
                "impact_level_numeric": 1,
                "est_pax": 50,
                "est_cost_usd": 1000.0,
            },
            {
                "flight_no": "VN300",
                "aircraft_reg": "VN-B999",
                "impact_level_numeric": None,
                "est_pax": 0,
                "est_cost_usd": 0.0,
            },
        ]
    )
    opts = suggest_recovery_options(df)
    flights_in_order = [o.flight_no for o in opts]
    # All VN100 options come before all VN200 options (sort key: flight_no first)
    assert flights_in_order == sorted(flights_in_order)


def test_swap_candidate_is_first_free_tail() -> None:
    df = _make_df(
        [
            {
                "flight_no": "VN100",
                "aircraft_reg": "VN-A001",
                "impact_level_numeric": 1,
                "est_pax": 180,
                "est_cost_usd": 5000.0,
            },
            {
                "flight_no": "VN999",
                "aircraft_reg": "VN-Z999",
                "impact_level_numeric": None,
            },
            {
                "flight_no": "VN888",
                "aircraft_reg": "VN-Y999",
                "impact_level_numeric": None,
            },
        ]
    )
    opts = suggest_recovery_options(df)
    swap = next(o for o in opts if o.option == "swap_tail")
    # Sorted ascending; "VN-Y999" < "VN-Z999"
    assert swap.swap_candidate_reg == "VN-Y999"
