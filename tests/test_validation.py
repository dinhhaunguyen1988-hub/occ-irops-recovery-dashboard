"""Tests for the pilot-readiness validation module."""

from __future__ import annotations

from io import StringIO

import pandas as pd
import pytest

from src.validation import (
    PREDICTED_LABELS,
    compute_precision_recall,
    parse_actuals_csv,
    validate_against_actuals,
)


def _make_predictions() -> pd.DataFrame:
    """Build a tiny predictions frame covering all four labels."""
    return pd.DataFrame(
        {
            "flight_no": ["VN101", "VN102", "VN103", "VN104", "VN105", "VN106"],
            "impact_level_numeric": [1, 1, 2, 3, None, None],
        }
    )


def test_parse_actuals_csv_strips_and_uppercases() -> None:
    csv = "flight_no,actual_outcome\n vn101 ,Cancelled\nvn102, Delayed \n,on_time\n"
    df = parse_actuals_csv(StringIO(csv))
    assert list(df["flight_no"]) == ["VN101", "VN102"]
    assert list(df["actual_outcome"]) == ["cancelled", "delayed"]


def test_parse_actuals_csv_rejects_missing_columns() -> None:
    with pytest.raises(ValueError):
        parse_actuals_csv(StringIO("foo,bar\n1,2\n"))


def test_validate_against_actuals_confusion_matrix_shape() -> None:
    preds = _make_predictions()
    actuals = pd.DataFrame(
        {
            "flight_no": ["VN101", "VN102", "VN103", "VN104", "VN105", "VN106"],
            "actual_outcome": [
                "cancelled",
                "on_time",
                "delayed",
                "cancelled",
                "on_time",
                "delayed",
            ],
        }
    )
    out = validate_against_actuals(preds, actuals)
    confusion = out["confusion"]
    assert set(confusion.columns) == {"predicted_label", "actual_outcome", "count"}
    assert confusion["count"].sum() == 6


def test_validate_aggregate_recall_catches_misses() -> None:
    """If we predict L1 for half of the actually-cancelled flights, recall should reflect it."""
    preds = pd.DataFrame(
        {
            "flight_no": ["A1", "A2", "A3", "A4"],
            "impact_level_numeric": [1, None, 1, None],
        }
    )
    actuals = pd.DataFrame(
        {
            "flight_no": ["A1", "A2", "A3", "A4"],
            "actual_outcome": ["cancelled", "cancelled", "on_time", "on_time"],
        }
    )
    out = validate_against_actuals(preds, actuals)
    metrics = out["metrics"].set_index("label")
    affected_row = metrics.loc["Affected (any)"]
    assert int(affected_row["tp"]) == 1  # A1
    assert int(affected_row["fp"]) == 1  # A3 predicted L1 but on_time
    assert int(affected_row["fn"]) == 1  # A2 missed
    assert affected_row["recall"] == pytest.approx(0.5)


def test_validate_unmatched_flight_counted_in_coverage() -> None:
    preds = _make_predictions()
    # actuals only cover 2 of 6 flights
    actuals = pd.DataFrame(
        {
            "flight_no": ["VN101", "VN104"],
            "actual_outcome": ["cancelled", "cancelled"],
        }
    )
    out = validate_against_actuals(preds, actuals)
    cov = out["coverage"].set_index("metric")["count"].to_dict()
    assert cov["matched"] == 2
    assert cov["unmatched"] == 4


def test_validate_empty_actuals_returns_empty_metrics() -> None:
    preds = _make_predictions()
    actuals = pd.DataFrame(columns=["flight_no", "actual_outcome"])
    out = validate_against_actuals(preds, actuals)
    assert out["confusion"].empty
    assert out["metrics"].empty


def test_predicted_labels_constant_includes_all_four() -> None:
    assert PREDICTED_LABELS == ("Not affected", "Level 1", "Level 2", "Level 3+")


def test_compute_precision_recall_handles_empty() -> None:
    out = compute_precision_recall(pd.DataFrame(columns=["predicted_label", "actual_outcome"]))
    assert out.empty
