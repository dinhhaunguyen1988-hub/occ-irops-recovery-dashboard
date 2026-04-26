"""Compare cascade predictions against actual operational outcomes.

Inputs
------
- ``predictions``: DataFrame produced by :func:`detect_cascade_multi`,
  which carries an ``impact_level_numeric`` column (None / 1 / 2 / 3+).
- ``actuals``: DataFrame with at least ``flight_no`` and
  ``actual_outcome`` columns. Outcomes are expected to be one of
  :data:`ACTUAL_OUTCOMES`. Optional ``flight_date`` column allows
  unambiguous joins when the same flight number repeats across days.

Outputs
-------
- ``confusion``: tidy long DataFrame ``(predicted_label, actual_outcome,
  count)``.
- ``metrics``: per-level precision / recall / f1 (Level 1, Level 2,
  Level 3+, and an aggregate "Affected" bucket).

Design intent
-------------
This is intentionally a small, deterministic, dependency-light module so
that the validation dashboard can be exercised in unit tests *without*
needing real AIMS files. Once real fixtures arrive, the same code path
runs end-to-end with no changes.
"""

from __future__ import annotations

from io import StringIO

import pandas as pd

# Canonical labels used in the confusion matrix.
PREDICTED_LABELS: tuple[str, ...] = (
    "Not affected",
    "Level 1",
    "Level 2",
    "Level 3+",
)

ACTUAL_OUTCOMES: tuple[str, ...] = (
    "on_time",
    "delayed",
    "cancelled",
    "diverted",
)


def _predicted_label(level: object) -> str:
    """Map ``impact_level_numeric`` to its canonical label."""
    try:
        if level is None or pd.isna(level):  # type: ignore[call-overload]
            return "Not affected"
    except (TypeError, ValueError):
        if level is None:
            return "Not affected"
    try:
        n = int(level)  # type: ignore[call-overload]
    except (TypeError, ValueError):
        return "Not affected"
    if n <= 0:
        return "Not affected"
    if n == 1:
        return "Level 1"
    if n == 2:
        return "Level 2"
    return "Level 3+"


def parse_actuals_csv(file_or_text: str | StringIO) -> pd.DataFrame:
    """Parse an actuals CSV (flight_no, actual_outcome[, flight_date]).

    Accepts either a path/buffer (anything pandas understands) or a raw
    CSV string. Returns a normalized DataFrame with stripped/uppercased
    flight numbers and lowercased outcomes; rows missing either column
    are dropped silently (callers can compare row counts to detect this).
    """
    df = pd.read_csv(file_or_text)
    df.columns = [str(c).strip().lower() for c in df.columns]
    if "flight_no" not in df.columns or "actual_outcome" not in df.columns:
        raise ValueError("actuals CSV must contain 'flight_no' and 'actual_outcome' columns")
    # Drop rows where either required cell is missing *before* stringifying, so
    # NaN does not silently become the literal string ``"NAN"``.
    df = df.dropna(subset=["flight_no", "actual_outcome"])
    df["flight_no"] = df["flight_no"].astype(str).str.strip().str.upper()
    df["actual_outcome"] = df["actual_outcome"].astype(str).str.strip().str.lower()
    df = df[df["flight_no"] != ""]
    df = df[df["actual_outcome"] != ""]
    # Defensive: post-stringification ``"nan"`` / ``"none"`` markers can still
    # appear if the source CSV uses them as literals. Treat them as missing.
    df = df[~df["flight_no"].str.lower().isin({"nan", "none"})]
    df = df[~df["actual_outcome"].isin({"nan", "none"})]
    return df.reset_index(drop=True)


def validate_against_actuals(
    predictions: pd.DataFrame,
    actuals: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    """Join predictions with actuals and return confusion + per-level metrics.

    The join is done on ``flight_no`` (and ``flight_date`` if present in
    both frames). Predictions with no matching actual row are dropped from
    the analysis but counted in the returned ``coverage`` summary so the
    UI can flag low-coverage runs.
    """
    if "flight_no" not in predictions.columns:
        raise ValueError("predictions must contain 'flight_no'")
    if "impact_level_numeric" not in predictions.columns:
        raise ValueError("predictions must contain 'impact_level_numeric'")

    pred = predictions.copy()
    pred["flight_no"] = pred["flight_no"].astype(str).str.strip().str.upper()
    pred["predicted_label"] = pred["impact_level_numeric"].apply(_predicted_label)

    join_keys = ["flight_no"]
    if "flight_date" in pred.columns and "flight_date" in actuals.columns:
        join_keys.append("flight_date")

    merged = pred.merge(actuals, on=join_keys, how="left", suffixes=("", "_act"))

    matched_mask = merged["actual_outcome"].notna()
    matched = merged[matched_mask].copy()

    confusion = compute_confusion_matrix(matched)
    metrics = compute_precision_recall(matched)
    coverage = pd.DataFrame(
        {
            "metric": ["predictions", "matched", "unmatched"],
            "count": [
                len(merged),
                int(matched_mask.sum()),
                int((~matched_mask).sum()),
            ],
        }
    )
    return {"confusion": confusion, "metrics": metrics, "coverage": coverage}


def compute_confusion_matrix(matched: pd.DataFrame) -> pd.DataFrame:
    """Return tidy long-form confusion matrix from a matched frame."""
    if matched.empty:
        return pd.DataFrame(columns=["predicted_label", "actual_outcome", "count"])
    grid = (
        matched.groupby(["predicted_label", "actual_outcome"])
        .size()
        .reset_index(name="count")
        .sort_values(["predicted_label", "actual_outcome"])
        .reset_index(drop=True)
    )
    return grid


def _affected_outcomes(outcome: str) -> bool:
    """An outcome counts as 'actually affected' if it is delayed/cancelled/diverted."""
    return outcome in {"delayed", "cancelled", "diverted"}


def compute_precision_recall(matched: pd.DataFrame) -> pd.DataFrame:
    """Compute precision / recall / f1 per predicted label.

    For each label, "affected" is the union of {delayed, cancelled,
    diverted} actuals; "Not affected" prediction is treated as the
    negative class. Aggregate "Affected" bucket merges Level 1+2+3+ to
    capture overall true-positive rate.
    """
    if matched.empty:
        return pd.DataFrame(columns=["label", "tp", "fp", "fn", "precision", "recall", "f1"])

    actual_affected = matched["actual_outcome"].apply(_affected_outcomes)

    rows: list[dict[str, float | str]] = []
    for label in PREDICTED_LABELS:
        if label == "Not affected":
            continue
        pred_pos = matched["predicted_label"] == label
        tp = int((pred_pos & actual_affected).sum())
        fp = int((pred_pos & ~actual_affected).sum())
        fn = int(
            (~pred_pos & actual_affected & (matched["predicted_label"] != "Not affected")).sum()
        )
        # Recall here is conditional on label set we control; aggregate
        # "Affected" row below gives the more meaningful global recall.
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
        rows.append(
            {
                "label": label,
                "tp": tp,
                "fp": fp,
                "fn": fn,
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "f1": round(f1, 4),
            }
        )

    # Aggregate "Affected" row: any Level 1/2/3+ prediction vs any affected actual.
    pred_any = matched["predicted_label"] != "Not affected"
    tp = int((pred_any & actual_affected).sum())
    fp = int((pred_any & ~actual_affected).sum())
    fn = int((~pred_any & actual_affected).sum())
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    rows.append(
        {
            "label": "Affected (any)",
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
        }
    )

    return pd.DataFrame(rows, columns=["label", "tp", "fp", "fn", "precision", "recall", "f1"])
