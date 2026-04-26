"""Passenger reaccommodation priority list.

Without real PNR data, this is a heuristic ranking based on:

1. International flag (intl > domestic)
2. Estimated pax count (more pax = higher priority for ops attention)
3. Cascade depth (deeper cascade = more downstream impact)

The list is meant as a *starting point* for the rebooking team — they
still own the final reaccommodation decisions.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class PaxReaccommodationRow:
    rank: int
    flight_no: str
    aircraft_reg: str | None
    origin: str
    destination: str
    is_international: bool
    est_pax: int
    cascade_depth: int
    impact_level: int
    rationale: str


def _is_international(orig: str | None, dest: str | None) -> bool:
    """Return True if either endpoint is outside Vietnam.

    Vietnam IATA codes start with letters that match the
    domestic-airport list. Anything else is treated as international.
    The list is small enough to inline; if it grows, factor into
    ``src/config.py``.
    """
    domestic = {
        "HAN",
        "SGN",
        "DAD",
        "CXR",
        "VCA",
        "HPH",
        "VII",
        "UIH",
        "PXU",
        "VCS",
        "DLI",
        "TBB",
        "VKG",
        "BMV",
        "VCL",
        "CAH",
        "DIN",
        "HUI",
        "VDH",
        "VDO",
    }
    o = (orig or "").upper().strip()
    d = (dest or "").upper().strip()
    if not o or not d:
        return False
    return not (o in domestic and d in domestic)


def build_reaccommodation_list(
    df_result: pd.DataFrame,
    only_levels: tuple[int, ...] = (1, 2, 3, 4, 5),
) -> list[PaxReaccommodationRow]:
    """Return affected flights ranked for the rebooking team.

    Sort priority: international ▼, est_pax ▼, cascade_depth ▼.
    """
    if df_result.empty:
        return []

    affected = df_result[df_result["impact_level_numeric"].isin(only_levels)].copy()
    if affected.empty:
        return []

    affected["is_intl"] = affected.apply(
        lambda r: _is_international(r.get("origin"), r.get("destination")),
        axis=1,
    )
    affected = affected.sort_values(
        by=["is_intl", "est_pax", "cascade_depth"],
        ascending=[False, False, False],
        kind="mergesort",
    ).reset_index(drop=True)

    rows: list[PaxReaccommodationRow] = []
    for rank, (_, r) in enumerate(affected.iterrows(), start=1):
        intl = bool(r.get("is_intl", False))
        pax = int(r.get("est_pax", 0) or 0)
        depth = int(r.get("cascade_depth", 0) or 0)
        level = int(r.get("impact_level_numeric", 0) or 0)
        rationale_parts = []
        if intl:
            rationale_parts.append("International")
        if pax > 200:
            rationale_parts.append("High pax load")
        if depth >= 2:
            rationale_parts.append(f"Cascade depth {depth}")
        if level == 1:
            rationale_parts.append("Direct closure impact")
        rationale = "; ".join(rationale_parts) or "Standard priority"

        reg_raw = r.get("aircraft_reg")
        rows.append(
            PaxReaccommodationRow(
                rank=rank,
                flight_no=str(r.get("flight_no", "?")),
                aircraft_reg=str(reg_raw) if pd.notna(reg_raw) else None,
                origin=str(r.get("origin", "")),
                destination=str(r.get("destination", "")),
                is_international=intl,
                est_pax=pax,
                cascade_depth=depth,
                impact_level=level,
                rationale=rationale,
            )
        )

    return rows
