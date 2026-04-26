"""Pilot-readiness validation utilities.

Used to compare cascade predictions against actual operational outcomes
once the dashboard is live in OCC. The :func:`validate_against_actuals`
function consumes a small ``actuals`` table (one row per flight) and
returns a confusion matrix plus precision/recall per impact level.
"""

from src.validation.validator import (
    ACTUAL_OUTCOMES,
    PREDICTED_LABELS,
    compute_confusion_matrix,
    compute_precision_recall,
    parse_actuals_csv,
    validate_against_actuals,
)

__all__ = [
    "ACTUAL_OUTCOMES",
    "PREDICTED_LABELS",
    "compute_confusion_matrix",
    "compute_precision_recall",
    "parse_actuals_csv",
    "validate_against_actuals",
]
