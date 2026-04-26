"""Two-pass cascade detection for airport closure impact analysis.

Pass 1: Detect all Level 1 flights independently (arrival into or departure
        from closed airport within the closure time window).
Pass 2: Trace downstream cascade by aircraft registration, sorted by STD.

Boundary rule: start inclusive, end exclusive.
    time >= closure_start AND time < closure_end
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from src.models.event import AirportClosureEvent


def display_impact_level(level: int | None) -> str:
    """Convert numeric impact level to display string.

    1  -> "Level 1"
    2  -> "Level 2"
    3+ -> "3+"
    None -> "Not affected"
    """
    if level is None:
        return "Not affected"
    if level == 1:
        return "Level 1"
    if level == 2:
        return "Level 2"
    return "3+"


def _impact_reason(level: int | None, is_dest: bool, is_orig: bool) -> str:
    """Generate a human-readable reason for the impact level."""
    if level is None:
        return ""
    if level == 1:
        parts = []
        if is_dest:
            parts.append("Arrival into closed airport")
        if is_orig:
            parts.append("Departure from closed airport")
        return "; ".join(parts) if parts else "Direct impact"
    if level == 2:
        return "Downstream aircraft rotation after Level 1 impact"
    return "Extended downstream cascade"


def detect_cascade(
    df: pd.DataFrame,
    event: AirportClosureEvent,
) -> pd.DataFrame:
    """Run two-pass cascade detection.

    Parameters
    ----------
    df : pd.DataFrame
        Flight data with canonical columns including ``origin``,
        ``destination``, ``std``, ``sta``, ``aircraft_reg``, ``flight_no``.
    event : AirportClosureEvent
        Airport closure event definition.

    Returns
    -------
    pd.DataFrame
        Input dataframe augmented with cascade columns:
        ``impact_level_numeric``, ``impact_level_display``,
        ``impact_reason``, ``cascade_root_flight``.
    """
    df = df.copy()

    # Initialize cascade columns
    df["impact_level_numeric"] = None
    df["impact_reason"] = ""
    df["cascade_root_flight"] = None

    # --- Pass 1: Detect all Level 1 flights ---
    dest_affected = pd.Series(False, index=df.index)
    orig_affected = pd.Series(False, index=df.index)

    if "destination" in df.columns and "sta" in df.columns:
        dest_affected = (
            (df["destination"] == event.airport)
            & (df["sta"].notna())
            & (df["sta"] >= event.start_time)
            & (df["sta"] < event.end_time)
        )

    if "origin" in df.columns and "std" in df.columns:
        orig_affected = (
            (df["origin"] == event.airport)
            & (df["std"].notna())
            & (df["std"] >= event.start_time)
            & (df["std"] < event.end_time)
        )

    level1_mask = dest_affected | orig_affected
    df.loc[level1_mask, "impact_level_numeric"] = 1

    # Set reasons for Level 1
    for idx in df[level1_mask].index:
        is_dest = bool(dest_affected.at[idx]) if idx in dest_affected.index else False
        is_orig = bool(orig_affected.at[idx]) if idx in orig_affected.index else False
        df.at[idx, "impact_reason"] = _impact_reason(1, is_dest, is_orig)
        df.at[idx, "cascade_root_flight"] = df.at[idx, "flight_no"]

    # --- Pass 2: Trace downstream by aircraft registration ---
    if "aircraft_reg" in df.columns and "std" in df.columns:
        for reg_key, group in df.groupby("aircraft_reg", dropna=False):
            reg: Any = reg_key
            try:
                if reg is None or pd.isna(reg):
                    continue
            except (TypeError, ValueError):
                pass

            sorted_group = group.sort_values("std", na_position="last")
            cascade_level: int | None = None
            root_flight: str | None = None

            for idx, row in sorted_group.iterrows():
                if row["impact_level_numeric"] == 1:
                    cascade_level = 2
                    root_flight = row["flight_no"]
                elif cascade_level is not None:
                    if row["impact_level_numeric"] is None:
                        df.at[idx, "impact_level_numeric"] = cascade_level
                        df.at[idx, "impact_reason"] = _impact_reason(cascade_level, False, False)
                        df.at[idx, "cascade_root_flight"] = root_flight
                    cascade_level += 1

    # --- Generate display level ---
    df["impact_level_display"] = df["impact_level_numeric"].apply(display_impact_level)

    return df


def compute_kpis(df: pd.DataFrame) -> dict:
    """Compute summary KPIs from cascade-analysed dataframe.

    Returns
    -------
    dict with keys:
        total_flights, affected_flights, level_1_count, level_2_count,
        level_3plus_count, aircraft_affected
    """
    affected = df[df["impact_level_numeric"].notna()]

    level_1 = affected[affected["impact_level_numeric"] == 1]
    level_2 = affected[affected["impact_level_numeric"] == 2]
    level_3plus = affected[affected["impact_level_numeric"] >= 3]

    aircraft_affected = (
        affected["aircraft_reg"].nunique() if "aircraft_reg" in affected.columns else 0
    )

    return {
        "total_flights": len(df),
        "affected_flights": len(affected),
        "level_1_count": len(level_1),
        "level_2_count": len(level_2),
        "level_3plus_count": len(level_3plus),
        "aircraft_affected": aircraft_affected,
    }
