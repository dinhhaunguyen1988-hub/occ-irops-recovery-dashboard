"""Two-pass cascade detection for airport closure impact analysis.

Pass 1: Detect all Level 1 flights independently (arrival into or departure
        from a closed airport within the closure time window).
Pass 2: Trace downstream cascade by aircraft registration, sorted by
        ``(flight_date, std)`` for correct propagation across overnight rotations.

Boundary rule: start inclusive, end exclusive.
    time >= closure_start AND time < closure_end

Multi-airport closure (Sprint 3): when multiple events are passed, Pass 1 is
run as the *union* of per-event Level-1 masks (a flight only needs to satisfy
one event to be Level 1). Pass 2 runs once on the combined Level-1 set, so
the cascade chain reflects the full multi-event impact rather than being
fragmented per event.
"""

from __future__ import annotations

from collections.abc import Iterable
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


def _level1_masks_for_event(
    df: pd.DataFrame, event: AirportClosureEvent
) -> tuple[pd.Series, pd.Series]:
    """Return (dest_affected, orig_affected) boolean masks for a single event."""
    on_closure_date = pd.Series(True, index=df.index)
    if "flight_date" in df.columns:
        on_closure_date = df["flight_date"] == event.closure_date

    dest_affected = pd.Series(False, index=df.index)
    orig_affected = pd.Series(False, index=df.index)

    if "destination" in df.columns and "sta" in df.columns:
        dest_affected = (
            (df["destination"] == event.airport)
            & (df["sta"].notna())
            & (df["sta"] >= event.start_time)
            & (df["sta"] < event.end_time)
            & on_closure_date
        )

    if "origin" in df.columns and "std" in df.columns:
        orig_affected = (
            (df["origin"] == event.airport)
            & (df["std"].notna())
            & (df["std"] >= event.start_time)
            & (df["std"] < event.end_time)
            & on_closure_date
        )

    return dest_affected, orig_affected


def detect_cascade_multi(
    df: pd.DataFrame,
    events: Iterable[AirportClosureEvent],
) -> pd.DataFrame:
    """Two-pass cascade detection across one or more closure events.

    Pass 1 takes the *union* of per-event Level-1 masks. Pass 2 runs once
    on the combined Level-1 set so a single cascade chain is produced per
    aircraft regardless of how many events touched it.
    """
    events_list = list(events)
    if not events_list:
        raise ValueError("detect_cascade_multi requires at least one closure event")

    df = df.copy()

    # Initialize cascade columns
    df["impact_level_numeric"] = None
    df["impact_reason"] = ""
    df["cascade_root_flight"] = None
    df["cascade_depth"] = 0

    # --- Pass 1: union of per-event Level-1 masks ---
    dest_union = pd.Series(False, index=df.index)
    orig_union = pd.Series(False, index=df.index)
    for event in events_list:
        dest_e, orig_e = _level1_masks_for_event(df, event)
        dest_union = dest_union | dest_e
        orig_union = orig_union | orig_e

    level1_mask = dest_union | orig_union
    df.loc[level1_mask, "impact_level_numeric"] = 1

    # Set reasons for Level 1 (combined across events)
    for idx in df[level1_mask].index:
        is_dest = bool(dest_union.at[idx])
        is_orig = bool(orig_union.at[idx])
        df.at[idx, "impact_reason"] = _impact_reason(1, is_dest, is_orig)
        df.at[idx, "cascade_root_flight"] = df.at[idx, "flight_no"]

    # --- Pass 2: trace downstream cascade by aircraft registration ---
    # Sort within each aircraft group by (flight_date, std) so cascade
    # propagates correctly across overnight rotations.
    sort_keys = [k for k in ("flight_date", "std") if k in df.columns]
    if "aircraft_reg" in df.columns and sort_keys:
        for reg_key, group in df.groupby("aircraft_reg", dropna=False):
            reg: Any = reg_key
            try:
                if reg is None or pd.isna(reg):
                    continue
            except (TypeError, ValueError):
                pass

            sorted_group = group.sort_values(sort_keys, na_position="last")
            cascade_level: int | None = None
            root_flight: str | None = None
            root_idx: Any = None
            depth: int = 0

            for idx, row in sorted_group.iterrows():
                if row["impact_level_numeric"] == 1:
                    cascade_level = 2
                    root_flight = row["flight_no"]
                    root_idx = idx
                    depth = 0
                elif cascade_level is not None:
                    if row["impact_level_numeric"] is None:
                        df.at[idx, "impact_level_numeric"] = cascade_level
                        df.at[idx, "impact_reason"] = _impact_reason(cascade_level, False, False)
                        df.at[idx, "cascade_root_flight"] = root_flight
                    depth += 1
                    if root_idx is not None:
                        df.at[root_idx, "cascade_depth"] = depth
                    cascade_level += 1

    df["impact_level_display"] = df["impact_level_numeric"].apply(display_impact_level)

    return df


def detect_cascade(
    df: pd.DataFrame,
    event: AirportClosureEvent,
) -> pd.DataFrame:
    """Run two-pass cascade detection for a single closure event.

    Thin shim around :func:`detect_cascade_multi` for callers that only have
    one event. Behaviour is byte-identical to the previous single-event API.
    """
    return detect_cascade_multi(df, [event])


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
