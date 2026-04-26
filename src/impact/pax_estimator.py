"""Rule-based pax + cost impact estimation.

This module is deliberately simple and transparent. Every assumption is
config-overridable so DM / Finance can plug in real numbers when Phase 0
collects them. The intent is *not* to predict cost precisely, but to give
OCC a quick relative ranking signal beyond Level / cascade depth.

Components:
- ``est_pax`` = ``seat_capacity[aircraft_type] * load_factor``
- ``est_delay_minutes`` = mapping by impact level (configurable)
- ``est_cost_usd`` = ``est_pax * est_delay_minutes * cost_per_pax_per_minute``

A flight with no impact (``impact_level_numeric is None``) has zero delay
minutes and therefore zero cost; pax estimate is still populated so the
column exists uniformly across the dataframe.
"""

from __future__ import annotations

import pandas as pd

# Approximate Vietnam Airlines configurations (publicly known; replace with
# real fleet config when available).
DEFAULT_SEAT_CAPACITY: dict[str, int] = {
    "A321": 184,
    "A320": 168,
    "A330": 290,
    "A350": 305,
    "B787": 274,
    "B777": 295,
    "ATR": 68,
    "ATR72": 68,
}

DEFAULT_LOAD_FACTOR: float = 0.85

# Rough handle on operational delay per impact level. These are the
# ranking-purpose defaults used by the dashboard; expect Phase 0 data to
# refine them.
LEVEL_DELAY_MINUTES: dict[int, int] = {
    1: 240,  # Direct hit: typical 4h disruption (recovery + rebook)
    2: 120,  # Downstream rotation hit
    3: 60,  # Extended cascade
    4: 30,
    5: 15,
}

# Default cost per pax per minute of delay (USD). Rough industry figure;
# overridable via the function parameter.
DEFAULT_COST_PER_PAX_PER_MINUTE: float = 0.50


def _seat_capacity(aircraft_type: object, table: dict[str, int]) -> int:
    if aircraft_type is None:
        return 0
    key = str(aircraft_type).strip().upper()
    if not key:
        return 0
    if key in table:
        return table[key]
    # Try common prefix match (e.g. "A321NEO" -> "A321")
    for fleet_key, cap in table.items():
        if key.startswith(fleet_key):
            return cap
    return 0


def _delay_minutes(level: object, table: dict[int, int]) -> int:
    if level is None:
        return 0
    try:
        if pd.isna(level):  # type: ignore[call-overload]
            return 0
    except (TypeError, ValueError):
        pass
    try:
        lvl = int(level)  # type: ignore[call-overload]
    except (TypeError, ValueError):
        return 0
    if lvl in table:
        return table[lvl]
    if lvl >= max(table.keys()):
        return table[max(table.keys())]
    return 0


def estimate_pax_and_cost(
    df: pd.DataFrame,
    seat_capacity: dict[str, int] | None = None,
    load_factor: float = DEFAULT_LOAD_FACTOR,
    level_delay_minutes: dict[int, int] | None = None,
    cost_per_pax_per_minute: float = DEFAULT_COST_PER_PAX_PER_MINUTE,
) -> pd.DataFrame:
    """Add ``est_pax``, ``est_delay_minutes`` and ``est_cost_usd`` columns.

    Operates on a copy; existing columns of the same name are overwritten
    so the function is safe to call after parameter changes.
    """
    if seat_capacity is None:
        seat_capacity = DEFAULT_SEAT_CAPACITY
    if level_delay_minutes is None:
        level_delay_minutes = LEVEL_DELAY_MINUTES

    out = df.copy()

    pax: list[int] = []
    delay: list[int] = []
    cost: list[float] = []

    for _, row in out.iterrows():
        ac_type = row.get("aircraft_type")
        cap = _seat_capacity(ac_type, seat_capacity)
        est_pax = int(round(cap * load_factor))

        level = row.get("impact_level_numeric")
        d = _delay_minutes(level, level_delay_minutes)

        c = est_pax * d * cost_per_pax_per_minute

        pax.append(est_pax)
        delay.append(d)
        cost.append(round(c, 2))

    out["est_pax"] = pax
    out["est_delay_minutes"] = delay
    out["est_cost_usd"] = cost
    return out
