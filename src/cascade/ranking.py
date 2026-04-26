"""Priority ranking for affected flights.

The score is intentionally simple and transparent — it is intended to help
OCC review the most impactful flights first, not to replace operational
judgement.

Components (weights chosen for readable scores):
- impact_level: Level 1 = 100, Level 2 = 60, Level 3+ = 30
- cascade_depth (Level 1 only): + 10 per downstream sector
- international route: + 20 (origin or destination is non-VN)
"""

from __future__ import annotations

import pandas as pd

VN_AIRPORTS = {
    "HAN",
    "SGN",
    "DAD",
    "HPH",
    "VCA",
    "VCS",
    "PXU",
    "VKG",
    "TBB",
    "UIH",
    "VCL",
    "DLI",
    "VDO",
    "BMV",
    "DIN",
    "HUI",
    "CXR",
    "VII",
}


def _level_score(level: int | None) -> int:
    if level == 1:
        return 100
    if level == 2:
        return 60
    if level is None:
        return 0
    return 30  # Level 3+


def _is_international(origin: object, destination: object) -> bool:
    o = str(origin).strip().upper() if origin is not None else ""
    d = str(destination).strip().upper() if destination is not None else ""
    if not o or not d:
        return False
    return (o not in VN_AIRPORTS) or (d not in VN_AIRPORTS)


def compute_priority(df: pd.DataFrame) -> pd.DataFrame:
    """Add a ``priority_score`` column to ``df`` (in-place safe — copy first).

    Higher score = review first. Score is 0 for unaffected flights.
    """
    out = df.copy()
    if "priority_score" in out.columns:
        out = out.drop(columns=["priority_score"])

    scores: list[int] = []
    for _, row in out.iterrows():
        raw_level = row.get("impact_level_numeric")
        try:
            level: int | None = int(raw_level) if pd.notna(raw_level) else None
        except (TypeError, ValueError):
            level = None
        score = _level_score(level)
        if level == 1:
            depth = row.get("cascade_depth", 0) or 0
            try:
                score += int(depth) * 10
            except (TypeError, ValueError):
                pass
        if _is_international(row.get("origin"), row.get("destination")):
            score += 20
        scores.append(score)

    out["priority_score"] = scores
    return out
